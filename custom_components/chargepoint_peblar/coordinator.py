"""DataUpdateCoordinator for the ChargePoint (Peblar) local API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    ChargePointApiError,
    ChargePointAuthError,
    ChargePointClient,
    ChargePointConnectionError,
    ChargePointRateLimitError,
)
from .const import (
    DATA_EVINTERFACE,
    DATA_HEALTH,
    DATA_METER,
    DATA_SYSTEM,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ChargePointCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates polling of /health + /system + /evinterface + /meter."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ChargePointClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the coordinator."""
        self.client = client
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({client.host})",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the four resources in parallel.

        /health is included so HA picks up runtime AccessMode changes; it
        is unauthenticated and cheap. Four GETs per cycle stay well below
        the charger's 5 req/s shared rate limit.
        """
        try:
            system, evinterface, meter, health = await asyncio.gather(
                self.client.async_get_system(),
                self.client.async_get_evinterface(),
                self.client.async_get_meter(),
                self.client.async_get_health(),
            )
        except ChargePointAuthError as err:
            # Triggers the reauth flow on the config entry. The user is
            # prompted to enter a new token; on success the entry is
            # reloaded with the new credentials.
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except ChargePointRateLimitError as err:
            raise UpdateFailed(f"Rate limited by charger: {err}") from err
        except ChargePointConnectionError as err:
            raise UpdateFailed(f"Cannot reach charger: {err}") from err
        except ChargePointApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

        return {
            DATA_SYSTEM: system,
            DATA_EVINTERFACE: evinterface,
            DATA_METER: meter,
            DATA_HEALTH: health,
        }
