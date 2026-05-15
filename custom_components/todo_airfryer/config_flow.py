"""Config flow for the Todo AirFryer integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import dhcp
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import config_validation as cv

from .const import CONF_FRYER_IP, CONF_PASSWORD, DEFAULT_PASSWORD, DOMAIN
from .pysmartlive import AirFryerClient


class TodoAirFryerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Todo AirFryer."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_ip: str | None = None

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> ConfigFlowResult:
        """Triggered by DHCP discovery (MAC OUI + hostname match)."""
        await self.async_set_unique_id(discovery_info.ip)
        self._abort_if_unique_id_configured(updates={CONF_FRYER_IP: discovery_info.ip})
        self._discovered_ip = discovery_info.ip
        self.context["title_placeholders"] = {"ip": discovery_info.ip}
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            fryer_ip = user_input[CONF_FRYER_IP]
            password = user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD)

            await self.async_set_unique_id(fryer_ip)
            self._abort_if_unique_id_configured()

            try:
                await self.hass.async_add_executor_job(_probe, fryer_ip, password.encode())
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Todo AirFryer ({fryer_ip})",
                    data={CONF_FRYER_IP: fryer_ip, CONF_PASSWORD: password},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_FRYER_IP, default=self._discovered_ip or vol.UNDEFINED): cv.string,
                vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): cv.string,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


def _probe(fryer_ip: str, password: bytes) -> None:
    with AirFryerClient(fryer_ip=fryer_ip, password=password) as client:
        client.get_status()
