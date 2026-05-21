"""Sensor entities for the ChargePoint (Peblar) local API integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CP_STATE_DESCRIPTIONS,
    DATA_EVINTERFACE,
    DATA_METER,
    DATA_SYSTEM,
    DOMAIN,
    RUNTIME_COORDINATOR,
)
from .coordinator import ChargePointCoordinator
from .entity import ChargePointEntity


@dataclass(frozen=True, kw_only=True)
class ChargePointSensorEntityDescription(SensorEntityDescription):
    """Describes a ChargePoint sensor.

    `source` selects which payload to read from ("evinterface", "meter",
    or "system"); `value_fn` extracts and converts the raw value.
    """

    source: str
    value_fn: Callable[[dict[str, Any]], Any]
    extra_state_attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _ma_to_a(raw: Any) -> float | None:
    """Convert milliamps to amps."""
    if raw is None:
        return None
    try:
        return round(float(raw) / 1000.0, 3)
    except (TypeError, ValueError):
        return None


def _wh_to_kwh(raw: Any) -> float | None:
    """Convert watt-hours to kilowatt-hours.

    Empirically observed (via diagnostics from a 1.8.0+1+CHARGEPOINT-1
    firmware): EnergyTotal=406142 ≈ 406 kWh lifetime, EnergySession=7294
    ≈ 7.3 kWh per session — both consistent with Wh as the raw unit.
    If your charger reports values 1000x too high, your firmware uses
    mWh — change the divisor below to 1_000_000.
    """
    if raw is None:
        return None
    try:
        return round(float(raw) / 1000.0, 3)
    except (TypeError, ValueError):
        return None


def _passthrough(key: str) -> Callable[[dict[str, Any]], Any]:
    """Return a value_fn that just returns payload[key]."""

    def _fn(payload: dict[str, Any]) -> Any:
        return payload.get(key)

    return _fn


def _passthrough_any(*keys: str) -> Callable[[dict[str, Any]], Any]:
    """Return a value_fn that returns the first non-None value among keys.

    Used to tolerate firmware variants that disagree on field casing
    (e.g. WlanSignalStrength vs WLANSignalStrength).
    """

    def _fn(payload: dict[str, Any]) -> Any:
        for k in keys:
            v = payload.get(k)
            if v is not None:
                return v
        return None

    return _fn


def _ma_from(key: str) -> Callable[[dict[str, Any]], Any]:
    def _fn(payload: dict[str, Any]) -> Any:
        return _ma_to_a(payload.get(key))

    return _fn


def _wh_from(key: str) -> Callable[[dict[str, Any]], Any]:
    def _fn(payload: dict[str, Any]) -> Any:
        return _wh_to_kwh(payload.get(key))

    return _fn


def _cp_state_value(payload: dict[str, Any]) -> str | None:
    raw = payload.get("CpState")
    if raw is None:
        return None
    return CP_STATE_DESCRIPTIONS.get(raw, raw)


def _cp_state_attrs(payload: dict[str, Any]) -> dict[str, Any]:
    return {"raw_state": payload.get("CpState")}


def _error_codes_value(payload: dict[str, Any]) -> int | None:
    codes = payload.get("ActiveErrorCodes")
    if codes is None:
        return None
    return len(codes)


def _error_codes_attrs(payload: dict[str, Any]) -> dict[str, Any]:
    return {"codes": payload.get("ActiveErrorCodes") or []}


def _warning_codes_value(payload: dict[str, Any]) -> int | None:
    codes = payload.get("ActiveWarningCodes")
    if codes is None:
        return None
    return len(codes)


def _warning_codes_attrs(payload: dict[str, Any]) -> dict[str, Any]:
    return {"codes": payload.get("ActiveWarningCodes") or []}


# --- Description tables ---------------------------------------------------

EVINTERFACE_SENSORS: tuple[ChargePointSensorEntityDescription, ...] = (
    ChargePointSensorEntityDescription(
        key="cp_state",
        translation_key="cp_state",
        name="Status",
        source=DATA_EVINTERFACE,
        value_fn=_cp_state_value,
        extra_state_attributes_fn=_cp_state_attrs,
    ),
    ChargePointSensorEntityDescription(
        key="charge_current_limit",
        name="Charge current limit",
        source=DATA_EVINTERFACE,
        value_fn=_ma_from("ChargeCurrentLimit"),
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
    ),
    ChargePointSensorEntityDescription(
        key="charge_current_limit_actual",
        name="Charge current limit (actual)",
        source=DATA_EVINTERFACE,
        value_fn=_ma_from("ChargeCurrentLimitActual"),
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
    ),
    ChargePointSensorEntityDescription(
        key="charge_current_limit_source",
        name="Charge current limit source",
        source=DATA_EVINTERFACE,
        value_fn=_passthrough("ChargeCurrentLimitSource"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


def _meter_phase_descriptions() -> tuple[ChargePointSensorEntityDescription, ...]:
    items: list[ChargePointSensorEntityDescription] = []
    for phase in (1, 2, 3):
        items.append(
            ChargePointSensorEntityDescription(
                key=f"current_phase_{phase}",
                name=f"Current L{phase}",
                source=DATA_METER,
                value_fn=_ma_from(f"CurrentPhase{phase}"),
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                suggested_display_precision=2,
            )
        )
        items.append(
            ChargePointSensorEntityDescription(
                key=f"voltage_phase_{phase}",
                name=f"Voltage L{phase}",
                source=DATA_METER,
                value_fn=_passthrough(f"VoltagePhase{phase}"),
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                suggested_display_precision=0,
            )
        )
        items.append(
            ChargePointSensorEntityDescription(
                key=f"power_phase_{phase}",
                name=f"Power L{phase}",
                source=DATA_METER,
                value_fn=_passthrough(f"PowerPhase{phase}"),
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.WATT,
                suggested_display_precision=0,
            )
        )
    return tuple(items)


METER_SENSORS: tuple[ChargePointSensorEntityDescription, ...] = (
    *_meter_phase_descriptions(),
    ChargePointSensorEntityDescription(
        key="power_total",
        name="Power total",
        source=DATA_METER,
        value_fn=_passthrough("PowerTotal"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
    ),
    ChargePointSensorEntityDescription(
        key="energy_total",
        name="Energy total",
        source=DATA_METER,
        value_fn=_wh_from("EnergyTotal"),
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    ChargePointSensorEntityDescription(
        key="energy_session",
        name="Energy session",
        source=DATA_METER,
        value_fn=_wh_from("EnergySession"),
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
)


SYSTEM_SENSORS: tuple[ChargePointSensorEntityDescription, ...] = (
    ChargePointSensorEntityDescription(
        key="wlan_signal_strength",
        name="WLAN signal strength",
        source=DATA_SYSTEM,
        # Firmware variants disagree on capitalisation; try both.
        value_fn=_passthrough_any("WlanSignalStrength", "WLANSignalStrength"),
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    ChargePointSensorEntityDescription(
        key="cellular_signal_strength",
        name="Cellular signal strength",
        source=DATA_SYSTEM,
        value_fn=_passthrough("CellularSignalStrength"),
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ChargePointSensorEntityDescription(
        key="uptime",
        name="Uptime",
        source=DATA_SYSTEM,
        value_fn=_passthrough("Uptime"),
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ChargePointSensorEntityDescription(
        key="firmware_version",
        name="Firmware version",
        source=DATA_SYSTEM,
        value_fn=_passthrough("FirmwareVersion"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ChargePointSensorEntityDescription(
        key="active_error_codes",
        name="Active error codes",
        source=DATA_SYSTEM,
        value_fn=_error_codes_value,
        extra_state_attributes_fn=_error_codes_attrs,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ChargePointSensorEntityDescription(
        key="active_warning_codes",
        name="Active warning codes",
        source=DATA_SYSTEM,
        value_fn=_warning_codes_value,
        extra_state_attributes_fn=_warning_codes_attrs,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


ALL_SENSORS: tuple[ChargePointSensorEntityDescription, ...] = (
    *EVINTERFACE_SENSORS,
    *METER_SENSORS,
    *SYSTEM_SENSORS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a config entry."""
    coordinator: ChargePointCoordinator = hass.data[DOMAIN][entry.entry_id][
        RUNTIME_COORDINATOR
    ]
    async_add_entities(
        ChargePointSensor(coordinator, description) for description in ALL_SENSORS
    )


class ChargePointSensor(ChargePointEntity, SensorEntity):
    """A single ChargePoint sensor backed by an entity description."""

    entity_description: ChargePointSensorEntityDescription

    def __init__(
        self,
        coordinator: ChargePointCoordinator,
        description: ChargePointSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._serial}_{description.key}"

    def _payload(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.entity_description.source, {}) or {}

    @property
    def native_value(self) -> Any:
        """Return the current value of the sensor."""
        return self.entity_description.value_fn(self._payload())

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return any per-sensor extra attributes."""
        fn = self.entity_description.extra_state_attributes_fn
        if fn is None:
            return None
        return fn(self._payload())
