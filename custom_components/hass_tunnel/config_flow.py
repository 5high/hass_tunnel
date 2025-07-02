from __future__ import annotations

import logging
from typing import Any

import aiohttp
import asyncio
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import issue_registry as ir
from homeassistant.loader import async_get_integration

from ruamel.yaml import YAML

from .const import DOMAIN, AUTH_URL, WEBSITE

import os
from pathlib import Path


_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            "username",
        ): str,
        vol.Required(
            "password",
        ): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    session = async_get_clientsession(hass)
    payload = {
        "username": data[CONF_USERNAME],
        "password": data[CONF_PASSWORD],
    }

    _LOGGER.debug(f"Trying to authenticate with {AUTH_URL}")

    try:
        async with session.post(AUTH_URL, json=payload, timeout=10) as response:
            if response.status == 200:
                _LOGGER.info("Authentication successful")
            elif response.status in (401, 403, 400):
                _LOGGER.warning("Authentication failed: Invalid credentials")
                # raise InvalidAuth
                try:
                    error_json = await response.json()
                    message = error_json.get("message", "认证失败")
                except Exception:
                    message = "Authentication failed"
                raise AuthFailedWithMessage(message)
            else:
                _LOGGER.error(f"Connection failed: HTTP status {response.status}")
                raise CannotConnect

    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        _LOGGER.error(f"Unable to connect to API server: {exc}")
        raise CannotConnect


class AuthFailedWithMessage(HomeAssistantError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the HA Tunnel configuration flow."""

    VERSION = 1

    async def ensure_http_proxy_config(self):
        # 常见的配置文件路径列表（可按需扩展）
        CONFIG_PATHS = [
            "config/configuration.yaml",
            "/config/configuration.yaml",
        ]

        def find_config_file():
            for path in CONFIG_PATHS:
                if os.path.exists(path):
                    return path
            _LOGGER.warning("couldn't find any Home Assistant configuration file")
            return None

        def _sync_update():
            CONFIG_FILE = find_config_file()
            if not CONFIG_FILE or not os.path.exists(CONFIG_FILE):
                _LOGGER.warning(f"Config file missing: {CONFIG_FILE}, skipping update")
                return

            yaml = YAML()
            yaml.preserve_quotes = True

            with open(CONFIG_FILE, "r") as f:
                config = yaml.load(f) or {}

            http_config = config.get("http", {})
            changed = False

            if not isinstance(http_config, dict):
                http_config = {}
                changed = True

            if not http_config.get("use_x_forwarded_for", False):
                http_config["use_x_forwarded_for"] = True
                changed = True

            trusted_proxies = http_config.get("trusted_proxies", [])
            if not isinstance(trusted_proxies, list):
                trusted_proxies = []
                changed = True

            if "127.0.0.1" not in trusted_proxies:
                trusted_proxies.append("127.0.0.1")
                http_config["trusted_proxies"] = trusted_proxies
                changed = True

            if changed:
                config["http"] = http_config
                with open(CONFIG_FILE, "w") as f:
                    yaml.dump(config, f)
                _LOGGER.info(f"HTTP configuration updated in {CONFIG_FILE}")
            else:
                _LOGGER.info("HTTP configuration already present, no update needed")

        await self.hass.async_add_executor_job(_sync_update)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except AuthFailedWithMessage as e:
                errors["base"] = "auth_failed_custom"
                self._custom_error_message = e.message  # 保存自定义错误文本
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception during authentication")
                errors["base"] = "unknown"
            else:
                # Load integration name from manifest and store in entry data
                integration = await async_get_integration(self.hass, DOMAIN)
                name = integration.manifest.get("name", DOMAIN)
                await self.ensure_http_proxy_config()

                # 在创建配置条目之前添加重启建议
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    "restart_required_after_config",
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="restart_required_after_config",
                    translation_placeholders={"integration_name": name},
                )

                return self.async_create_entry(
                    title=name,
                    data={**user_input, "name": name},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "get_credentials_url": WEBSITE,
                "custom_error": getattr(self, "_custom_error_message", ""),
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
