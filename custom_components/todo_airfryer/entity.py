"""Shared entity base for the Todo AirFryer."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import TodoAirFryerCoordinator


class TodoAirFryerEntity(CoordinatorEntity[TodoAirFryerCoordinator]):
    """Base class for all Todo AirFryer entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TodoAirFryerCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.fryer_ip}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.fryer_ip)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"Todo AirFryer ({coordinator.fryer_ip})",
            configuration_url=f"http://{coordinator.fryer_ip}/",
        )
