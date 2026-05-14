"""Number platform for Todo AirFryer (temperature, time)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TodoAirFryerCoordinator
from .entity import TodoAirFryerEntity
from .pysmartlive.client import TEMP_MAX_C, TEMP_MIN_C, TIME_MAX_MIN, TIME_MIN_MIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TodoAirFryerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TemperatureNumber(coordinator),
            TimeNumber(coordinator),
        ]
    )


class TemperatureNumber(TodoAirFryerEntity, NumberEntity):
    _attr_translation_key = "temperature"
    _attr_native_min_value = TEMP_MIN_C
    _attr_native_max_value = TEMP_MAX_C
    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator: TodoAirFryerCoordinator) -> None:
        super().__init__(coordinator, "temperature")
        self._pending: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._pending

    async def async_set_native_value(self, value: float) -> None:
        self._pending = value
        await self.coordinator.async_send_temperature(int(value))
        self.async_write_ha_state()


class TimeNumber(TodoAirFryerEntity, NumberEntity):
    _attr_translation_key = "time"
    _attr_native_min_value = TIME_MIN_MIN
    _attr_native_max_value = TIME_MAX_MIN
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:timer"

    def __init__(self, coordinator: TodoAirFryerCoordinator) -> None:
        super().__init__(coordinator, "time")
        self._pending: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._pending

    async def async_set_native_value(self, value: float) -> None:
        self._pending = value
        await self.coordinator.async_send_time(int(value))
        self.async_write_ha_state()
