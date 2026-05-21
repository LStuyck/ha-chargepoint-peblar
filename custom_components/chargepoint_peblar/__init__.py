"""The ChargePoint (Peblar) local API integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ChargePointClient
from .const import (
    ACCESS_MODE_READWRITE,
    CONF_API_TOKEN,
    DATA_EVINTERFACE,
    DATA_HEALTH,
    DOMAIN,
    RUNTIME_ACCESS_MODE,
    RUNTIME_COORDINATOR,
    RUNTIME_MAX_CURRENT_MA,
)
from .coordinator import ChargePointCoordinator
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)

# Platforms loaded for every config entry.
PLATFORMS_READONLY: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Platforms only loaded when the charger exposes a writable API.
PLATFORMS_READWRITE: list[Platform] = [Platform.NUMBER, Platform.SWITCH]

READONLY_ISSUE_ID = "readonly_access_{entry_id}"


def _readonly_issue_id(entry_id: str) -> str:
    return READONLY_ISSUE_ID.format(entry_id=entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ChargePoint from a config entry."""
    session = async_get_clientsession(hass)
    client = ChargePointClient(
        host=entry.data[CONF_HOST],
        api_token=entry.data[CONF_API_TOKEN],
        session=session,
    )

    coordinator = ChargePointCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady("Initial refresh failed")

    # Snapshot the current ChargeCurrentLimit (mA) as the Number entity's
    # cap. Change the limit in the charger's web UI and reload to raise it.
    evinterface: dict[str, Any] = coordinator.data.get(DATA_EVINTERFACE, {}) or {}
    health: dict[str, Any] = coordinator.data.get(DATA_HEALTH, {}) or {}
    snapshot_ma = evinterface.get("ChargeCurrentLimit")
    access_mode = health.get("AccessMode")

    runtime: dict[str, Any] = {
        RUNTIME_COORDINATOR: coordinator,
        RUNTIME_ACCESS_MODE: access_mode,
        RUNTIME_MAX_CURRENT_MA: snapshot_ma,
    }
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    platforms = list(PLATFORMS_READONLY)

    if access_mode == ACCESS_MODE_READWRITE:
        platforms.extend(PLATFORMS_READWRITE)
        # Clear any previously-raised ReadOnly issue if the user has
        # switched the charger to ReadWrite since last setup.
        ir.async_delete_issue(hass, DOMAIN, _readonly_issue_id(entry.entry_id))
    else:
        _LOGGER.warning(
            "Charger at %s reports AccessMode=%r. Write entities will NOT "
            "be created. Enable ReadWrite in the charger's advanced settings "
            "and reload the integration to expose them.",
            entry.data[CONF_HOST],
            access_mode,
        )
        # Surface this as a repair issue so it's actionable from the UI
        # rather than buried in the log.
        ir.async_create_issue(
            hass,
            DOMAIN,
            _readonly_issue_id(entry.entry_id),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="readonly_access",
            translation_placeholders={
                "host": entry.data[CONF_HOST],
                "title": entry.title,
            },
            learn_more_url=(
                "https://github.com/LStuyck/ha-chargepoint-peblar" "#troubleshooting"
            ),
        )

    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    async_register_services(hass)
    runtime["platforms"] = platforms
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    runtime: dict[str, Any] = hass.data[DOMAIN].get(entry.entry_id, {})
    platforms: list[Platform] = runtime.get("platforms", PLATFORMS_READONLY)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        # Drop the repair issue too so it doesn't linger after removal.
        ir.async_delete_issue(hass, DOMAIN, _readonly_issue_id(entry.entry_id))
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            async_unregister_services(hass)

    return unload_ok
