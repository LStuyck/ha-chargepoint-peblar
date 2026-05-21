"""Binary sensor entities for the ChargePoint (Peblar) local API."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CP_STATES_CHARGING,
    CP_STATES_VEHICLE_CONNECTED,
    DATA_EVINTERFACE,
    DATA_SYSTEM,
    DOMAIN,
    RUNTIME_COORDINATOR,
)
from .coordinator import ChargePointCoordinator
from .entity import ChargePointEntity


@dataclass(frozen=True, kw_only=True)
class ChargePointBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a ChargePoint binary sensor."""

    source: str
    value_fn: Callable[[dict[str, Any]], bool | None]


def _is_charging(payload: dict[str, Any]) -> bool | None:
    state = payload.get("CpState")
    if state is None:
        return None
    return state in CP_STATES_CHARGING


def _vehicle_connected(payload: dict[str, Any]) -> bool | None:
    state = payload.get("CpState")
    if state is None:
        return None
    return state in CP_STATES_VEHICLE_CONNECTED


def _lock_state(payload: dict[str, Any]) -> bool | None:
    val = payload.get("LockState")
    if val is None:
        return None
    return bool(val)


def _force_one_phase(payload: dict[str, Any]) -> bool | None:
    val = payload.get("Force1Phase")
    if val is None:
        return None
    return bool(val)


def _has_errors(payload: dict[str, Any]) -> bool | None:
    codes = payload.get("ActiveErrorCodes")
    if codes is None:
        return None
    return len(codes) > 0


def _has_warnings(payload: dict[str, Any]) -> bool | None:
    codes = payload.get("ActiveWarningCodes")
    if codes is None:
        return None
    return len(codes) > 0


BINARY_SENSORS: tuple[ChargePointBinarySensorEntityDescription, ...] = (
    ChargePointBinarySensorEntityDescription(
        key="charging",
        name="Charging",
        source=DATA_EVINTERFACE,
        value_fn=_is_charging,
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    ChargePointBinarySensorEntityDescription(
        key="vehicle_connected",
        name="Vehicle connected",
        source=DATA_EVINTERFACE,
        value_fn=_vehicle_connected,
        device_class=BinarySensorDeviceClass.PLUG,
    ),
    ChargePointBinarySensorEntityDescription(
        key="cable_locked",
        name="Cable locked",
        source=DATA_EVINTERFACE,
        value_fn=_lock_state,
        device_class=BinarySensorDeviceClass.LOCK,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ChargePointBinarySensorEntityDescription(
        key="force_one_phase",
        name="Force 1-phase",
        source=DATA_EVINTERFACE,
        value_fn=_force_one_phase,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ChargePointBinarySensorEntityDescription(
        key="has_errors",
        name="Has errors",
        source=DATA_SYSTEM,
        value_fn=_has_errors,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    ChargePointBinarySensorEntityDescription(
        key="has_warnings",
        name="Has warnings",
        source=DATA_SYSTEM,
        value_fn=_has_warnings,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for a config entry."""
    coordinator: ChargePointCoordinator = hass.data[DOMAIN][entry.entry_id][
        RUNTIME_COORDINATOR
    ]
    async_add_entities(
        ChargePointBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class ChargePointBinarySensor(ChargePointEntity, BinarySensorEntity):
    """A single ChargePoint binary sensor."""

    entity_description: ChargePointBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ChargePointCoordinator,
        description: ChargePointBinarySensorEntityDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._serial}_{description.key}"

    def _payload(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.entity_description.source, {}) or {}

    @property
    def is_on(self) -> bool | None:
        """Return the current binary state."""
     