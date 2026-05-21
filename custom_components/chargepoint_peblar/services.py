"""Services for the ChargePoint (Peblar) local API integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import ChargePointApiError
from .const import (
    ACCESS_MODE_READWRITE,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DEVICE_ID,
    ATTR_METHOD,
    ATTR_TOKEN,
    DOMAIN,
    RUNTIME_ACCESS_MODE,
    RUNTIME_COORDINATOR,
    SERVICE_AUTHORIZE_CHARGE_SESSION,
)
from .coordinator import ChargePointCoordinator

_LOGGER = logging.getLogger(__name__)

# Either a device_id (preferred from the UI) or a raw config_entry_id is OK.
AUTHORIZE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(ATTR_DEVICE_ID, "target"): cv.string,
        vol.Exclusive(ATTR_CONFIG_ENTRY_ID, "target"): cv.string,
        vol.Required(ATTR_METHOD): cv.string,
        vol.Required(ATTR_TOKEN): cv.string,
    }
)


def _resolve_runtime(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Find the integration runtime for the targeted entry."""
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)

    if entry_id is None:
        device_id = call.data.get(ATTR_DEVICE_ID)
        if not device_id:
            raise ServiceValidationError(
                "Either device_id or config_entry_id must be provided"
            )
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Unknown device_id: {device_id}")
        for eid in device.config_entries:
            if eid in hass.data.get(DOMAIN, {}):
                entry_id = eid
                break
        if entry_id is None:
            raise ServiceValidationError(
                "Selected device is not a ChargePoint integration device"
            )

    runtime = hass.data.get(DOMAIN, {}).get(entry_id)
    if runtime is None:
        raise ServiceValidationError(
            f"No loaded ChargePoint entry for entry_id {entry_id}"
        )
    return runtime


async def _async_authorize(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the authorize_charge_session service call."""
    runtime = _resolve_runtime(hass, call)
    access_mode = runtime.get(RUNTIME_ACCESS_MODE)
    if access_mode != ACCESS_MODE_READWRITE:
        raise HomeAssistantError(
            f"Charger AccessMode is {access_mode!r}; the authorize endpoint "
            "requires ReadWrite. Enable it in the charger's advanced "
            "settings and reload the integration."
        )

    coordinator: ChargePointCoordinator = runtime[RUNTIME_COORDINATOR]
    method = call.data[ATTR_METHOD]
    token = call.data[ATTR_TOKEN]

    try:
        await coordinator.client.async_authorize_charge_session(method, token)
    except ChargePointApiError as err:
        raise HomeAssistantError(f"authorize_charge_session failed: {err}") from err

    # The API replies 202 and asks the caller to monitor session state. Kick
    # a refresh so HA picks up the new evinterface / system state ASAP.
    await coordinator.async_request_refresh()


def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_AUTHORIZE_CHARGE_SESSION):
        return

    async def _handler(call: ServiceCall) -> None:
        await _async_authorize(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_AUTHORIZE_CHARGE_SESSION,
        _handler,
        schema=AUTHORIZE_SCHEMA,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_AUTHORIZE_CHARGE_SESSION):
        hass.services.async_remove(DOMAIN, SERVICE_AUTHORIZE_CHARGE_SESSION)
