"""Config flow for the Todo AirFryer integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CLIENT_IP,
    CONF_CLIENT_PORT,
    CONF_FRYER_IP,
    CONF_PASSWORD,
    DEFAULT_CLIENT_PORT,
    DEFAULT_PASSWORD,
    DOMAIN,
)
from .pysmartlive import AirFryerClient


class TodoAirFryerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Todo AirFryer."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            fryer_ip = user_input[CONF_FRYER_IP]
            client_ip = user_input[CONF_CLIENT_IP]
            client_port = user_input.get(CONF_CLIENT_PORT, DEFAULT_CLIENT_PORT)
            password = user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD)

            await self.async_set_unique_id(fryer_ip)
            self._abort_if_unique_id_configured()

            try:
                await self.hass.async_add_executor_job(
                    _probe, fryer_ip, client_ip, client_port, password.encode()
                )
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Todo AirFryer ({fryer_ip})",
                    data={
                        CONF_FRYER_IP: fryer_ip,
                        CONF_CLIENT_IP: client_ip,
                        CONF_CLIENT_PORT: client_port,
                        CONF_PASSWORD: password,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_FRYER_IP): cv.string,
                vol.Required(CONF_CLIENT_IP): cv.string,
                vol.Optional(CONF_CLIENT_PORT, default=DEFAULT_CLIENT_PORT): cv.port,
                vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): cv.string,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


def _probe(fryer_ip: str, client_ip: str, client_port: int, password: bytes) -> None:
    with AirFryerClient(
        fryer_ip=fryer_ip,
        client_ip=client_ip,
        client_port=client_port,
        password=password,
    ) as client:
        client.get_status()
