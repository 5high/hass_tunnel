# HA Tunnel

**HA Tunnel** 是一个为 Home Assistant 提供内网穿透服务的集成。适用于无法直接从公网访问 Home Assistant 的用户。

![logo](https://github.com/5high/hass_tunnel/icon.png)

## ✨ 功能特点

- 自动建立安全的远程访问隧道
- 支持开机自动重连
- 配置简单，集成即用
- 登录验证机制，保障连接安全

## 🔧 安装方法

> **Home Assistant 2026.11 起，官方已内置 Marketplace（商店）并取代 HACS。**
> HACS 无法再安装到 2026.11 及以上版本；此前用 HACS 装过的用户，升级后 Marketplace 会自动接管，无需重装。

### 方式一：Marketplace（Home Assistant 2026.11 及以上，推荐）

[![在 Marketplace 中打开](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=5high&repository=hass_tunnel&category=integration)

1. 进入 **设置 > Marketplace**（仅管理员可见），首次打开需确认社区内容安全提示
2. 点右上角「⋮」> 「通过链接添加仓库」，填入：`https://github.com/5high/hass_tunnel`
   （或在 Marketplace 搜索框直接搜索 "HA Tunnel"）
3. 点击「安装」。部分版本需重启 Home Assistant 后生效（界面会提示）
4. 进入 **设置 > 设备与服务**，点「添加集成」，搜索并选择 `HA Tunnel`

### 方式二：HACS（Home Assistant 2026.10 及更早版本）

1. 打开 HACS > 集成 > 三个点 > 自定义存储库
2. 添加仓库地址 `https://github.com/5high/hass_tunnel`，类型选择 "集成"
3. 搜索 "HA Tunnel" 并安装
4. 安装完成后重启 Home Assistant
5. 进入设置 > 集成，点击添加集成，搜索并选择 `HA Tunnel`

### 方式三：手动安装（任意版本均可用）

1. 从 https://5high.top/ha_tunnel.zip 下载集成压缩包
2. 解压后把 `hass_tunnel` 文件夹放入 Home Assistant 配置目录的 `custom_components/` 下
3. 重启 Home Assistant
4. 进入 设置 > 设备与服务，添加集成，搜索 "HA Tunnel"

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
