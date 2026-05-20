"""Constants for the ChargePoint (Peblar) local API integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "chargepoint"
MANUFACTURER: Final = "ChargePoint"

# Config entry keys
CONF_HOST: Final = "host"
CONF_API_TOKEN: Final = "api_token"

# API
API_BASE_PATH: Final = "/api/wlac/v1"
API_TIMEOUT_SECONDS: Final = 10

# Polling
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=10)

# Endpoints (relative to API_BASE_PATH)
ENDPOINT_HEALTH: Final = "/health"
ENDPOINT_SYSTEM: Final = "/system"
ENDPOINT_EVINTERFACE: Final = "/evinterface"
ENDPOINT_METER: Final = "/meter"

# Data keys used in coordinator.data
DATA_SYSTEM: Final = "system"
DATA_EVINTERFACE: Final = "evinterface"
DATA_METER: Final = "meter"
DATA_HEALTH: Final = "health"

# /health AccessMode values
ACCESS_MODE_READWRITE: Final = "ReadWrite"

# Entry runtime-data keys
RUNTIME_COORDINATOR: Final = "coordinator"
RUNTIME_ACCESS_MODE: Final = "access_mode"
RUNTIME_MAX_CURRENT_MA: Final = "max_current_ma"

# Number entity bounds
MIN_CHARGE_CURRENT_A: Final = 6.0
DEFAULT_MAX_CHARGE_CURRENT_A: Final = 16.0

# Service
SERVICE_AUTHORIZE_CHARGE_SESSION: Final = "authorize_charge_session"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_DEVICE_ID: Final = "device_id"
ATTR_METHOD: Final = "method"
ATTR_TOKEN: Final = "token"

# IEC 61851 control-pilot state mapping.
CP_STATE_DESCRIPTIONS: Final[dict[str, str]] = {
    "State A": "No vehicle",
    "State B": "Vehicle connected",
    "State C": "Charging",
    "State D": "Charging (ventilation)",
    "State E": "Error",
    "State F": "Fault",
}

CP_STATES_VEHICLE_CONNECTED: Final = frozenset(
    {"State B", "State C", "State D", "State E"}
)
CP_STATES_CHARGING: Final = frozenset({"State C", "State D"})
