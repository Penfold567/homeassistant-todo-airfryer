"""Button platform for Todo AirFryer (start, stop)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TodoAirFryerCoordinator
from .entity import TodoAirFryerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TodoAirFryerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            StartButton(coordinator),
            StopButton(coordinator),
        ]
    )


class StartButton(TodoAirFryerEntity, ButtonEntity):
    _attr_translation_key = "start"
    _attr_icon = "mdi:play"

    def __init__(self, coordinator: TodoAirFryerCoordinator) -> None:
        super().__init__(coordinator, "start")

    async def async_press(self) -> None:
        await self.coordinator.async_send_start()


class StopButton(TodoAirFryerEntity, ButtonEntity):
    _attr_translation_key = "stop"
    _attr_icon = "mdi:stop"

    def __init__(self, coordinator: TodoAirFryerCoordinator) -> None:
        super().__init__(coordinator, "stop")

    async def async_press(self) -> None:
        await self.coordinator.async_send_stop()
