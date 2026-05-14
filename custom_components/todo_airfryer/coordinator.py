"""DataUpdateCoordinator for the Todo AirFryer."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CLIENT_IP,
    CONF_CLIENT_PORT,
    CONF_FRYER_IP,
    CONF_PASSWORD,
    DEFAULT_CLIENT_PORT,
    DEFAULT_PASSWORD,
    DOMAIN,
    UPDATE_INTERVAL,
)
from .pysmartlive import AirFryerClient
from .pysmartlive.client import AirFryerStatus

_LOGGER = logging.getLogger(__name__)


class TodoAirFryerCoordinator(DataUpdateCoordinator[AirFryerStatus]):
    """Polls fryer status and serves it to entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_FRYER_IP]}",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.fryer_ip: str = entry.data[CONF_FRYER_IP]
        self.client_ip: str = entry.data[CONF_CLIENT_IP]
        self.client_port: int = entry.data.get(CONF_CLIENT_PORT, DEFAULT_CLIENT_PORT)
        self.password: bytes = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD).encode()

    def _build_client(self) -> AirFryerClient:
        return AirFryerClient(
            fryer_ip=self.fryer_ip,
            client_ip=self.client_ip,
            client_port=self.client_port,
            password=self.password,
        )

    async def _async_update_data(self) -> AirFryerStatus:
        def _fetch() -> AirFryerStatus:
            with self._build_client() as client:
                return client.get_status()

        try:
            return await self.hass.async_add_executor_job(_fetch)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"status fetch failed: {err}") from err

    async def async_send_temperature(self, celsius: int) -> None:
        def _do() -> None:
            with self._build_client() as client:
                client.set_temperature(celsius)

        await self.hass.async_add_executor_job(_do)
        await self.async_request_refresh()

    async def async_send_time(self, minutes: int) -> None:
        def _do() -> None:
            with self._build_client() as client:
                client.set_time(minutes)

        await self.hass.async_add_executor_job(_do)
        await self.async_request_refresh()

    async def async_send_fan(self, fan: int) -> None:
        def _do() -> None:
            with self._build_client() as client:
                client.set_fan(fan)

        await self.hass.async_add_executor_job(_do)
        await self.async_request_refresh()

    async def async_send_start(self) -> None:
        def _do() -> None:
            with self._build_client() as client:
                client.power_on()
                client.start()

        await self.hass.async_add_executor_job(_do)
        await self.async_request_refresh()

    async def async_send_stop(self) -> None:
        def _do() -> None:
            with self._build_client() as client:
                client.stop()

        await self.hass.async_add_executor_job(_do)
        await self.async_request_refresh()
