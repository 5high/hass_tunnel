# HA Tunnel

**HA Tunnel** 是一个为 Home Assistant 提供内网穿透服务的集成。适用于无法直接从公网访问 Home Assistant 的用户。

## ✨ 功能特点

- 自动建立安全的远程访问隧道
- 支持开机自动重连
- 配置简单，集成即用
- 登录验证机制，保障连接安全

## 🔧 安装方法（通过 HACS）

1. 打开 HACS > 集成 > 三个点 > 自定义存储库
2. 添加你的仓库地址（例如：`https://github.com/5high/hass_tunnel`），类型选择 “集成”
3. 搜索 “HA Tunnel” 并安装
4. 安装完成后重启 Home Assistant
5. 进入设置 > 集成，点击添加集成，搜索并选择 `HA Tunnel`

## 🧪 获取登录信息

请前往以下地址注册并获取账号信息：

[https://example.com](https://example.com)

> 注册后可获得专属访问地址及端口，用于配置集成

## 📘 使用说明

添加集成后，系统将自动建立隧道，无需额外设置。如遇连接失败，将通过通知栏提示详细错误信息。

## ❓ 常见问题

- **Q: 无法连接？**

  - 请检查是否填写了正确的用户名和密码
  - 确保本地 Home Assistant 端口可访问（如 8123）

- **Q: icon 没有显示？**
  - 请确认 `manifest.json` 中已添加 `"icon": "icon.png"`
  - 确保 `icon.png` 位于集成根目录，且尺寸建议为 256x256

## 📎 项目地址

GitHub: [https://github.com/5high/hass_tunnel](https://github.com/5high/hass_tunnel)

---

©️ 2025 由 @5high 开发维护
