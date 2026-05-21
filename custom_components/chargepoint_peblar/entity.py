"""Base entity for ChargePoint (Peblar) integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_SYSTEM, DOMAIN, MANUFACTURER
from .coordinator import ChargePointCoordinator


class ChargePointEntity(CoordinatorEntity[ChargePointCoordinator]):
    """Base entity that ties all sensors to a single device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ChargePointCoordinator) -> None:
        """Initialise the base entity."""
        super().__init__(coordinator)
        system: dict[str, Any] = coordinator.data.get(DATA_SYSTEM, {}) or {}
        serial = system.get("ProductSn") or coordinator.client.host
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=MANUFACTURER,
            model=system.get("ProductPn"),
            name=f"ChargePoint {serial}",
            sw_version=system.get("FirmwareVersion"),
            configuration_url=f"http://{coordinator.client.host}",
        )
        self._serial = serial

    def _system(self) -> dict[str, Any]:
        return self.coordinator.data.get(DATA_SYSTEM, {}) or {}

    def _evinterface(self) -> dict[str, Any]:
        return self.coordinator.data.get("evinterface", {}) or {}

    def _meter(self) -> dict[str, Any]:
        return self.coordinator.data.get("meter", {}) or {}
