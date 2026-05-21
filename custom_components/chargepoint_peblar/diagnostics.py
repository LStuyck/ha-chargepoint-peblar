"""Diagnostics support for the ChargePoint (Peblar) integration.

Provides the "Download diagnostics" button in HA's Devices & Services UI.
The downloaded JSON contains the latest coordinator payload (raw /health,
/system, /evinterface and /meter responses) plus the config entry, with
the API token redacted so the file can be shared in a public bug report.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_API_TOKEN,
    DOMAIN,
    RUNTIME_ACCESS_MODE,
    RUNTIME_COORDINATOR,
    RUNTIME_MAX_CURRENT_MA,
)

# Fields to remove from the output before sharing. Add anything sensitive here.
TO_REDACT = {CONF_API_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinator = runtime.get(RUNTIME_COORDINATOR)

    coordinator_info: dict[str, Any] = {}
    if coordinator is not None:
        coordinator_info = {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                repr(coordinator.last_exception)
                if coordinator.last_exception is not None
                else None
            ),
            "update_interval": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "data": coordinator.data,
        }

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "domain": entry.domain,
            "source": entry.source,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
            "unique_id": entry.unique_id,
        },
        "runtime": {
            "access_mode": runtime.get(RUNTIME_ACCESS_MODE),
            "max_current_ma": runtime.get(RUNTIME_MAX_CURRENT_MA),
            "platforms": runtime.get("platforms"),
        },
        "coordinator": coordinator_info,
    }
