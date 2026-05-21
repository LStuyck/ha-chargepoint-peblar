"""The ChargePoint (Peblar) local API integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
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

    # Snapshot the current ChargeCurrentLimit (mA). This becomes the cap of
    # the Number entity per the user's chosen strategy. To raise it later,
    # change the limit in the charger's web UI and reload the integration.
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

    # Always load read-only platforms.
    platforms = list(PLATFORMS_READONLY)

    if access_mode == ACCESS_MODE_READWRITE:
        platforms.extend(PLATFORMS_READWRITE)
    else:
        _LOGGER.warning(
            "Charger at %s reports AccessMode=%r. Write entities will NOT "
            "be created. Enable ReadWrite in the charger's advanced settings "
            "and reload the integration to expose them.",
            entry.data[CONF_HOST],
            access_mode,
        )

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # Services are domain-wide. Register once (idempotent inside helper).
    async_register_services(hass)

    # Remember which platforms we loaded so unload uses the same list.
    runtime["platforms"] = platforms

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    runtime: dict[str, Any] = hass.data[DOMAIN].get(entry.entry_id, {})
    platforms: list[Platform] = runtime.get("platforms", PLATFORMS_READONLY)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # If this was the last entry, drop the services too.
        if not hass.data[DOMAIN]:
            async_unregister_services(hass)

    return unload_ok
