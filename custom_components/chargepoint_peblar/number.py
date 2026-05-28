"""Number entity to set the ChargePoint charge current limit (in amps)."""

from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ChargePointApiError
from .const import (
    DATA_EVINTERFACE,
    DEFAULT_MAX_CHARGE_CURRENT_A,
    DOMAIN,
    MIN_CHARGE_CURRENT_A,
    RUNTIME_COORDINATOR,
    RUNTIME_MAX_CURRENT_MA,
)
from .coordinator import ChargePointCoordinator
from .entity import ChargePointEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the charge current limit number entity."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: ChargePointCoordinator = runtime[RUNTIME_COORDINATOR]
    snapshot_ma = runtime.get(RUNTIME_MAX_CURRENT_MA)

    if snapshot_ma is None or snapshot_ma <= 0:
        # We never saw a valid limit at setup; fall back to a sane default
        # rather than refusing to create the entity. The charger will reject
        # out-of-range writes anyway.
        max_amps = DEFAULT_MAX_CHARGE_CURRENT_A
        _LOGGER.info(
            "No ChargeCurrentLimit snapshot at setup; defaulting cap to %.1f A",
            max_amps,
        )
    else:
        max_amps = round(snapshot_ma / 1000.0, 1)

    async_add_entities([ChargePointCurrentLimitNumber(coordinator, max_amps)])


class ChargePointCurrentLimitNumber(ChargePointEntity, NumberEntity):
    """Number entity for ChargeCurrentLimit."""

    _attr_name = "Charge current limit (set)"
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = MIN_CHARGE_CURRENT_A
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: ChargePointCoordinator,
        max_amps: float,
    ) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._serial}_set_charge_current_limit"
        self._attr_native_max_value = max(max_amps, MIN_CHARGE_CURRENT_A)

    @property
    def native_value(self) -> float | None:
        """Return the current ChargeCurrentLimit in amps."""
        data = self.coordinator.data.get(DATA_EVINTERFACE) or {}
        raw = data.get("ChargeCurrentLimit")
        if raw is None:
            return None
        try:
            return round(float(raw) / 1000.0, 3)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """PATCH a new ChargeCurrentLimit (in mA)."""
        clamped = max(
            self._attr_native_min_value,
            min(self._attr_native_max_value, value),
        )
        if clamped != value:
            _LOGGER.warning(
                "Requested %.2f A clamped to %.2f A (entity bounds %.1f-%.1f A)",
                value,
                clamped,
                self._attr_native_min_value,
                self._attr_native_max_value,
            )
        ma = round(clamped * 1000)
        try:
            await self.coordinator.client.async_patch_evinterface(
                {"ChargeCurrentLimit": ma}
            )
        except ChargePointApiError as err:
            raise HomeAssistantError(
                f"Failed to set charge current limit: {err}"
            ) from err
        # Pull the new state so all entities reflect it immediately.
        await self.coordinator.async_request_refresh()
