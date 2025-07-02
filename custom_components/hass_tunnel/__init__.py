"""The HA Tunnel integration."""

from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import service
from .tunnel import ManagedTunnel
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Tunnel from a config entry."""
    try:
        _LOGGER.info(f"🧩 Setting up HA Tunnel ({entry.title})")

        tunnel = ManagedTunnel(entry, hass, local_port=hass.config.api.port)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = tunnel

        # 注册启动服务
        async def handle_start_tunnel(call: ServiceCall):
            """Service handler to start the tunnel."""
            _LOGGER.info("▶️ Service call received to START the tunnel.")
            await hass.async_add_executor_job(tunnel.start)
            _LOGGER.info("Tunnel start command issued.")

        hass.services.async_register(
            DOMAIN,
            "start_tunnel",
            handle_start_tunnel,
        )

        # 注册停止服务
        async def handle_stop_tunnel(call: ServiceCall):
            """Service handler to stop the tunnel."""
            _LOGGER.info("⏹️ Service call received to STOP the tunnel.")
            await hass.async_add_executor_job(tunnel.stop)
            _LOGGER.info("Tunnel stop command issued and completed.")

        hass.services.async_register(
            DOMAIN,
            "stop_tunnel",
            handle_stop_tunnel,
        )

        _LOGGER.info("🚀 Triggering initial tunnel start on setup...")

        await hass.async_add_executor_job(tunnel.start)

        return True

    except Exception as e:
        _LOGGER.exception("❌ Failed during setup_entry: %s", e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and stop the tunnel."""
    _LOGGER.info(f"🔌 Unloading HA Tunnel ({entry.title})")

    tunnel: ManagedTunnel = hass.data[DOMAIN].pop(entry.entry_id, None)

    if tunnel:
        await hass.async_add_executor_job(tunnel.stop)
        _LOGGER.info("Tunnel stopped successfully.")
    else:
        _LOGGER.warning("No tunnel found for this entry!")

    if not hass.data.get(DOMAIN):
        _LOGGER.info("Removing HA Tunnel services...")
        hass.services.async_remove(DOMAIN, "start_tunnel")
        hass.services.async_remove(DOMAIN, "stop_tunnel")

    return True
