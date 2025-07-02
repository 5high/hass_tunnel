import paramiko
import socket
import select
import threading
import time
import logging
import requests
import asyncio

from .const import AUTH_URL, WEBSITE

from homeassistant.helpers.translation import async_get_translations

# --- Basic Logging Setup ---
_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger("paramiko").setLevel(logging.WARNING)


class ParamikoFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "Error reading SSH protocol banner" not in record.getMessage()


paramiko_transport_logger = logging.getLogger("paramiko.transport")
paramiko_transport_logger.setLevel(logging.CRITICAL)
paramiko_transport_logger.propagate = False
paramiko_transport_logger.handlers.clear()
paramiko_transport_logger.addFilter(ParamikoFilter())


def login_successful(username, password, url):
    payload = {"username": username, "password": password}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        success = data.get("success", False) is True
        return success, data
    except requests.RequestException as e:
        _LOGGER.error(f"Login request failed: {e}")
        return False, {}


def login_with_retry(
    username, password, url, delay=2, backoff_factor=2, max_attempts=8
):
    attempt = 1
    while attempt <= max_attempts:
        success, data = login_successful(username, password, url)
        if success:
            return True, data
        else:
            _LOGGER.warning(f"Login attempt {attempt} failed. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= backoff_factor
            attempt += 1

    _LOGGER.error("Max login attempts reached. Login failed.")
    return False, None


class ForwardServer(threading.Thread):
    def __init__(
        self,
        transport,
        local_host,
        local_port,
        notify_func=None,
        entry=None,
        login_info=None,
    ):
        super().__init__()
        self.transport = transport
        self.remote_port = login_info.get("fwd_port")
        self.local_host = local_host
        self.local_port = local_port
        self.notify = notify_func
        self.SERVER_IP = login_info.get("tunnel_server")
        self.login_info = login_info or {}
        self.entry = entry
        self.daemon = True
        self._stop_event = threading.Event()

    def run(self):
        try:
            self.transport.request_port_forward("127.0.0.1", self.remote_port)
            _LOGGER.info(f"✅ Successfully started tunnel.")
            if self.notify:
                message = (
                    f"**✅ 隧道已成功建立！**\n\n"
                    f"- \U0001f4e1 专属访问地址：[{self.login_info.get('url')}]({self.login_info.get('url')})\n\n\n"
                    f"📘 [查看使用说明]({WEBSITE})"
                )
                self.notify(
                    f"{self.entry.data.get('name')} 启动成功",
                    message,
                    notification_id="hass_tunnel_started",
                )
        except Exception as e:
            _LOGGER.warning(f"⚠️ Failed to listen on tunnel server: {e}")

        while not self._stop_event.is_set() and self.transport.is_active():
            try:
                chan = self.transport.accept(timeout=1)
                if chan is None:
                    continue
                thr = threading.Thread(target=self.handler, args=(chan,), daemon=True)
                thr.start()
            except Exception:
                pass
        _LOGGER.info("Listener for remote port has stopped.")

    def handler(self, chan):
        try:
            with socket.create_connection((self.local_host, self.local_port)) as sock:
                # _LOGGER.info(f"🔁 Forwarding: {self.local_host}:{self.local_port}")
                while not self._stop_event.is_set():
                    r, _, _ = select.select([sock, chan], [], [], 1)
                    if not r:
                        continue
                    if sock in r:
                        data = sock.recv(4096)
                        if not data:
                            break
                        chan.send(data)
                    if chan in r:
                        data = chan.recv(4096)
                        if not data:
                            break
                        sock.send(data)
                # _LOGGER.info("🔚 Forwarding connection closed")
        except Exception as e:
            _LOGGER.warning("⚠️ Error during data forwarding")
        finally:
            chan.close()

    def stop(self):
        self._stop_event.set()
        try:
            self.transport.cancel_port_forward("127.0.0.1", self.remote_port)
            _LOGGER.info(f"✅ Tunnel service cancelled successfully")
        except Exception as e:
            _LOGGER.warning(f"❌ Failed to cancel port forwarding: {e}")


class ManagedTunnel:
    def __init__(self, entry, hass, local_port):
        self._lock = threading.Lock()
        self._is_running = False
        self.hass = hass
        self.entry = entry
        self.SERVER_PORT = 22
        self.LOCAL_HOST = "127.0.0.1"
        self.local_port = local_port

        self.tunnel_client = None
        self.forward_server = None
        self._maintain_thread = None
        self._stop_event = threading.Event()

    def _notify(self, title, message, notification_id="hass_tunnel_notification"):
        hass = getattr(self, "hass", None) or getattr(self.entry, "hass", None)
        if not hass:
            _LOGGER.warning("无法获取 Home Assistant 实例，无法发送通知")
            return

        asyncio.run_coroutine_threadsafe(
            hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": notification_id,
                },
                blocking=False,
            ),
            hass.loop,
        )

    def _maintain_loop(self):
        while not self._stop_event.is_set():
            try:
                success, info = login_with_retry(
                    self.entry.data["username"], self.entry.data["password"], AUTH_URL
                )
                if not success:
                    _LOGGER.warning("❌ Login failed")
                    message = (
                        f"**🚫 登录失败通知**\n\n"
                        f"- 👤 用户名: `{self.entry.data['username']}`\n"
                        f"- 🔐 ❌ 登录未成功，可能由于密码错误或服务器问题。\n问题修正后需要重启Home Assistant\n\n"
                        f"📘 [点击查看使用说明]({WEBSITE})"
                    )
                    self._notify(f"{self.entry.data.get('name')} 登录失败", message)
                    return  # 中断逻辑，不再继续

                self.tunnel_client = paramiko.SSHClient()
                self.tunnel_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                _LOGGER.info(f"🔗 Connecting to Tunnel server...")
                self.tunnel_client.connect(
                    info.get("tunnel_server"),
                    port=int(info.get("tunnel_port")),  # 如果为空就默认22
                    username=info.get("tunnel_user"),
                    password=info.get("tunnel_password"),
                    timeout=15,
                )
                self.tunnel_client.get_transport().set_keepalive(30)
                transport = self.tunnel_client.get_transport()
                if not transport:
                    raise Exception("Failed to get transport")

                self.forward_server = ForwardServer(
                    transport,
                    self.LOCAL_HOST,
                    self.local_port,
                    notify_func=self._notify,
                    entry=self.entry,
                    login_info=info,
                )
                self.forward_server.start()

                _LOGGER.info("🚀 Tunnel established")

                while transport.is_active() and not self._stop_event.is_set():
                    time.sleep(0.5)

            except Exception as e:
                _LOGGER.error(f"❌ Error during connection or maintenance ")
                message = (
                    f"**🚫 隧道连接失败**\n\n"
                    f"- ❗ ❌无法成功连接到服务器，可能是网络问题或认证失败。\n\n"
                    f"📘 [点击这里查看排查指南]({WEBSITE})"
                )
                self._notify(f"{self.entry.data.get('name')} ❌连接失败", message)

            finally:
                if self.tunnel_client:
                    try:
                        self.tunnel_client.close()
                        self.tunnel_client = None
                    except Exception:
                        pass

                if self.forward_server:
                    self.forward_server.stop()

                if not self._stop_event.is_set():
                    # _LOGGER.info("⏳ Retrying in 5 seconds...")
                    self._stop_event.wait(5)

        _LOGGER.info("Tunnel maintenance thread has fully stopped.")

    def start(self):
        with self._lock:
            if self._is_running:
                _LOGGER.warning("Tunnel is already running (checked by flag).")
                return
            self._stop_event.clear()
            self._is_running = True
            self._maintain_thread = threading.Thread(
                target=self._maintain_loop, daemon=True
            )
            self._maintain_thread.start()
            _LOGGER.info("Tunnel manager started.")

    def stop(self):
        _LOGGER.info("🛑 Stopping tunnel...")
        self._stop_event.set()

        if self.forward_server:
            self.forward_server.stop()
            self.forward_server = None

        if self.tunnel_client:
            self.tunnel_client.close()

        if self._maintain_thread:
            self._maintain_thread.join(timeout=7)
            if self._maintain_thread.is_alive():
                _LOGGER.warning("Maintenance thread did not shut down cleanly.")

        _LOGGER.info("Tunnel disconnected.")
        self._is_running = False
