"""Select platform for Todo AirFryer (fan)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TodoAirFryerCoordinator
from .entity import TodoAirFryerEntity

FAN_OPTIONS = ["1", "2", "3"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TodoAirFryerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FanSelect(coordinator)])


class FanSelect(TodoAirFryerEntity, SelectEntity):
    _attr_translation_key = "fan"
    _attr_options = FAN_OPTIONS
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: TodoAirFryerCoordinator) -> None:
        super().__init__(coordinator, "fan")
        self._pending: str | None = None

    @property
    def current_option(self) -> str | None:
        return self._pending

    async def async_select_option(self, option: str) -> None:
        self._pending = option
        await self.coordinator.async_send_fan(int(option))
        self.async_write_ha_state()
