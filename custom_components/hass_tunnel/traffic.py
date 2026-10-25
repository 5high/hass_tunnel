"""
隧道流量查询模块

供 HA 插件在通知里显示流量信息。

认证方式：使用用户自己的 5high.top 账号密码（插件配置里本来就有），
调用 POST {WEBSITE}/api/v1/traffic/self ，该接口只返回该用户自己的流量。
不需要服务器级 API token，因此可以安全地存在于公开仓库中。

数据来源：5high.top 服务端每 60 秒采样一次 SSH 隧道的 TCP 字节数，
写入数据库 tunnel_traffic 表。
"""

import logging
from datetime import datetime, timedelta

import requests

from .const import TRAFFIC_SELF_URL, WEBSITE

_LOGGER = logging.getLogger(__name__)

# 单次请求超时（秒）。流量查询失败不应该影响隧道本身。
REQUEST_TIMEOUT = 10


def format_bytes(num) -> str:
    """把字节数格式化成人类可读的字符串。"""
    try:
        num = float(num or 0)
    except (TypeError, ValueError):
        return "0 B"

    if num <= 0:
        return "0 B"

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            if unit == "B":
                return f"{int(num)} {unit}"
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def fetch_traffic(username: str, password: str, hours: int = 24) -> dict:
    """
    查询指定账号的隧道流量。

    返回 dict：
      {
        "ok": True,
        "summary": {
            "download_bytes": 123, "upload_bytes": 456, "total_bytes": 579,
            "download_cum": ..., "upload_cum": ...,
            "samples": 42, "last_seen": "2026-10-25 20:32:41",
        },
        "hourly": [ {"hour_bucket": ..., "download_bytes": ..., "upload_bytes": ...}, ... ],
      }

    查询失败时返回 {"ok": False, "error": "..."}，绝不抛异常。
    """
    if not username or not password:
        return {"ok": False, "error": "缺少账号或密码"}

    try:
        hours = max(1, min(int(hours or 24), 720))
    except (TypeError, ValueError):
        hours = 24

    try:
        response = requests.post(
            TRAFFIC_SELF_URL,
            json={"username": username, "password": password, "hours": hours},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        _LOGGER.warning("查询隧道流量失败: %s", e)
        return {"ok": False, "error": str(e)}

    if response.status_code != 200:
        _LOGGER.warning("查询隧道流量返回 HTTP %s", response.status_code)
        return {"ok": False, "error": f"HTTP {response.status_code}"}

    try:
        data = response.json()
    except ValueError as e:
        _LOGGER.warning("隧道流量响应不是合法 JSON: %s", e)
        return {"ok": False, "error": "invalid json"}

    if not data.get("success"):
        return {"ok": False, "error": data.get("message", "unknown error")}

    return {
        "ok": True,
        "hours": data.get("hours", hours),
        "summary": data.get("summary") or {},
        "hourly": data.get("hourly") or [],
    }


def build_traffic_message(traffic: dict, hours: int = 24) -> str:
    """
    把流量数据拼成通知用的 Markdown 文本。

    traffic 为 fetch_traffic() 的返回值。
    """
    if not traffic or not traffic.get("ok"):
        return ""

    summary = traffic.get("summary") or {}

    download = int(summary.get("download_bytes") or 0)
    upload = int(summary.get("upload_bytes") or 0)
    total = int(summary.get("total_bytes") or 0)
    samples = int(summary.get("samples") or 0)
    download_cum = int(summary.get("download_cum") or 0)
    upload_cum = int(summary.get("upload_cum") or 0)
    last_seen = summary.get("last_seen")

    lines = [
        "",
        f"**📊 近 {hours} 小时流量**",
        "",
        f"- ⬇️ 下行（服务器 → 你）：**{format_bytes(download)}**",
        f"- ⬆️ 上行（你 → 服务器）：**{format_bytes(upload)}**",
        f"- 📦 合计：**{format_bytes(total)}**",
    ]

    if download_cum or upload_cum:
        lines.append(
            f"- 🔗 本次连接累计：↓ {format_bytes(download_cum)} / ↑ {format_bytes(upload_cum)}"
        )

    if last_seen:
        lines.append(f"- 🕒 最后采样：{last_seen}")

    lines.append("")
    lines.append(f"📘 [查看完整流量统计]({WEBSITE}/traffic)")

    return "\n".join(lines)


def build_traffic_brief(traffic: dict, hours: int = 24) -> str:
    """
    一行式摘要，用于登录失败/连接失败等简短的提示里。
    """
    if not traffic or not traffic.get("ok"):
        return ""

    summary = traffic.get("summary") or {}
    total = int(summary.get("total_bytes") or 0)
    download = int(summary.get("download_bytes") or 0)
    upload = int(summary.get("upload_bytes") or 0)

    if total <= 0:
        return f"📊 近 {hours} 小时流量：暂无数据"

    return (
        f"📊 近 {hours} 小时流量：↓ {format_bytes(download)} / ↑ {format_bytes(upload)}"
        f"（合计 {format_bytes(total)}）"
    )
