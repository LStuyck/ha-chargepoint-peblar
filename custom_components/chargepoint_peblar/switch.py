"""Switch entity for the Force1Phase setting."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ChargePointApiError
from .const import (
    DATA_EVINTERFACE,
    DATA_SYSTEM,
    DOMAIN,
    RUNTIME_COORDINATOR,
)
from .coordinator import ChargePointCoordinator
from .entity import ChargePointEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Force1Phase switch if the hardware supports it."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: ChargePointCoordinator = runtime[RUNTIME_COORDINATOR]

    system: dict[str, Any] = coordinator.data.get(DATA_SYSTEM, {}) or {}
    if not system.get("Force1PhaseAllowed"):
        _LOGGER.info("Charger reports Force1PhaseAllowed=False; not adding the switch")
        return

    async_add_entities([ChargePointForce1PhaseSwitch(coordinator)])


class ChargePointForce1PhaseSwitch(ChargePointEntity, SwitchEntity):
    """Toggle Force1Phase via PATCH /evinterface."""

    _attr_name = "Force 1-phase"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ChargePointCoordinator) -> None:
        """Initialise the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._serial}_force_one_phase_switch"

    @property
    def is_on(self) -> bool | None:
        """Return whether Force1Phase is currently active."""
        data = self.coordinator.data.get(DATA_EVINTERFACE) or {}
        val = data.get("Force1Phase")
        if val is None:
            return None
        return bool(val)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn Force1Phase on."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn Force1Phase off."""
        await self._set(False)

    async def _set(self, value: bool) -> None:
        try:
            await self.coordinator.client.async_patch_evinterface(
                {"Force1Phase": value}
            )
        except ChargePointApiError as err:
            raise HomeAssistantError(f"Failed to set Force1Phase: {err}") from err
        await self.coordinator.async_request_refresh()
