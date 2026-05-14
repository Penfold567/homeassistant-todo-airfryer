"""Sensor platform for Todo AirFryer."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
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
            StateSensor(coordinator),
            RemainingMinutesSensor(coordinator),
        ]
    )


class StateSensor(TodoAirFryerEntity, SensorEntity):
    _attr_translation_key = "state"
    _attr_icon = "mdi:chef-hat"

    def __init__(self, coordinator: TodoAirFryerCoordinator) -> None:
        super().__init__(coordinator, "state")

    @property
    def native_value(self) -> str | None:
        if (data := self.coordinator.data) is None:
            return None
        return data.phase


class RemainingMinutesSensor(TodoAirFryerEntity, SensorEntity):
    _attr_translation_key = "remaining_minutes"
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: TodoAirFryerCoordinator) -> None:
        super().__init__(coordinator, "remaining_minutes")

    @property
    def native_value(self) -> int | None:
        if (data := self.coordinator.data) is None:
            return None
        return data.remaining_min_bucket
