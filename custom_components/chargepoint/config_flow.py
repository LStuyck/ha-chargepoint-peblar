"""Config flow for the ChargePoint (Peblar) local API integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
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


class ChargePointConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ChargePoint (Peblar)."""

    VERSION = 1

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
            except Exception:  # noqa: BLE001 - defensive log path
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
