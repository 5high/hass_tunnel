"""Constants for the HA Tunnel integration."""

DOMAIN = "hass_tunnel"
WEBSITE = "https://5high.top"
AUTH_URL = f"{WEBSITE}/api/v1/login"

# 用户自助流量查询接口（用用户自己的账号密码认证，只能查自己）
TRAFFIC_SELF_URL = f"{WEBSITE}/api/v1/traffic/self"

# MQTT 开通状态自查询接口（同样用用户自己的账号密码认证）
MQTT_SELF_URL = f"{WEBSITE}/api/v1/mqtt/self"

# 隧道在线期间流量通知的刷新间隔（秒）
TRAFFIC_REFRESH_SECONDS = 30 * 60
