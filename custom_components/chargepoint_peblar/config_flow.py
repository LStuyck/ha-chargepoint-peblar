"""Config flow for the ChargePoint (Peblar) local API integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ChargePointApiError,
    ChargePointAuthError,
    ChargePointClient,
    ChargePointConnectionError,
)
from .const import CONF_API_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_API_TOKEN): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): str,
    }
)


class ChargePointConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ChargePoint (Peblar)."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._reauth_entry: ConfigEntry | None = None

    # --- Initial setup -----------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step where the user enters host + token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            token = user_input[CONF_API_TOKEN].strip()

            session = async_get_clientsession(self.hass)
            client = ChargePointClient(host, token, session)

            try:
                system = await client.async_get_system()
            except ChargePointAuthError:
                errors["base"] = "invalid_auth"
            except ChargePointConnectionError:
                errors["base"] = "cannot_connect"
            except ChargePointApiError:
                errors["base"] = "unknown"
            except Exception:
                _LOGGER.exception("Unexpected error validating charger")
                errors["base"] = "unknown"
            else:
                serial = system.get("ProductSn")
                if not serial:
                    errors["base"] = "no_serial"
                else:
                    await self.async_set_unique_id(serial)
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: host}
                    )
                    product = system.get("ProductPn") or "ChargePoint"
                    return self.async_create_entry(
                        title=f"{product} ({serial})",
                        data={CONF_HOST: host, CONF_API_TOKEN: token},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    # --- Reauthentication --------------------------------------------------

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Trigger when the API token starts being rejected."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the reauth form and validate the new token."""
        assert self._reauth_entry is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            host = self._reauth_entry.data[CONF_HOST]
            new_token = user_input[CONF_API_TOKEN].strip()

            session = async_get_clientsession(self.hass)
            client = ChargePointClient(host, new_token, session)

            try:
                system = await client.async_get_system()
            except ChargePointAuthError:
                errors["base"] = "invalid_auth"
            except ChargePointConnectionError:
                errors["base"] = "cannot_connect"
            except ChargePointApiError:
                errors["base"] = "unknown"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                # Make sure the serial still matches the original entry to
                # prevent silently re-pointing this entry at a different
                # charger when someone reuses the IP.
                serial = system.get("ProductSn")
                if serial and serial != self._reauth_entry.unique_id:
                    errors["base"] = "wrong_device"
                else:
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data={
                            **self._reauth_entry.data,
                            CONF_API_TOKEN: new_token,
                        },
                    )
                    await self.hass.config_entries.async_reload(
                        self._reauth_entry.entry_id
                    )
                    return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "host": self._reauth_entry.data[CONF_HOST],
            },
        )
