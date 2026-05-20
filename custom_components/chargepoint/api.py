"""Async client for the Peblar / ChargePoint local REST API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError

from .const import (
    API_BASE_PATH,
    API_TIMEOUT_SECONDS,
    ENDPOINT_EVINTERFACE,
    ENDPOINT_HEALTH,
    ENDPOINT_METER,
    ENDPOINT_SYSTEM,
)

_LOGGER = logging.getLogger(__name__)


class ChargePointApiError(Exception):
    """Generic API error."""


class ChargePointAuthError(ChargePointApiError):
    """Raised on HTTP 401 - invalid or missing token."""


class ChargePointConnectionError(ChargePointApiError):
    """Raised on network / timeout failures."""


class ChargePointRateLimitError(ChargePointApiError):
    """Raised on HTTP 429."""


class ChargePointClient:
    """Minimal async client for the Peblar WLAC v1 REST API."""

    def __init__(
        self,
        host: str,
        api_token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._host = host.rstrip("/")
        self._token = api_token
        self._session = session
        self._base_url = f"http://{self._host}{API_BASE_PATH}"

    @property
    def host(self) -> str:
        return self._host

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
        require_auth: bool = True,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{endpoint}"
        headers: dict[str, str] = {"Accept": "application/json"}
        if require_auth:
            # The API uses the raw token, NOT a Bearer scheme.
            headers["Authorization"] = self._token
        if json is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with asyncio.timeout(API_TIMEOUT_SECONDS):
                async with self._session.request(
                    method, url, headers=headers, json=json
                ) as resp:
                    if resp.status == 401:
                        raise ChargePointAuthError(
                            "Unauthorized - check the API token"
                        )
                    if resp.status == 429:
                        raise ChargePointRateLimitError(
                            "Rate limit exceeded (5 req/s shared)"
                        )
                    if resp.status >= 400:
                        try:
                            body = await resp.json()
                            msg = body.get("statusmsg", f"HTTP {resp.status}")
                        except (ValueError, ClientResponseError):
                            msg = f"HTTP {resp.status}"
                        raise ChargePointApiError(msg)
                    return await resp.json()
        except asyncio.TimeoutError as err:
            raise ChargePointConnectionError(
                f"Timeout talking to {self._host}"
            ) from err
        except ClientError as err:
            raise ChargePointConnectionError(str(err)) from err

    # --- Read endpoints -----------------------------------------------------

    async def async_get_health(self) -> dict[str, Any]:
        return await self._request("GET", ENDPOINT_HEALTH, require_auth=False)

    async def async_get_system(self) -> dict[str, Any]:
        return await self._request("GET", ENDPOINT_SYSTEM)

    async def async_get_evinterface(self) -> dict[str, Any]:
        return await self._request("GET", ENDPOINT_EVINTERFACE)

    async def async_get_meter(self) -> dict[str, Any]:
        return await self._request("GET", ENDPOINT_METER)

    # --- Write endpoints ----------------------------------------------------

    async def async_patch_evinterface(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """PATCH /evinterface with a partial body."""
        return await self._request(
            "PATCH", ENDPOINT_EVINTERFACE, json=payload
        )

    async def async_authorize_charge_session(
        self, method: str, token: str
    ) -> None:
        """POST /authorization/charge-session. Returns None on 202 Accepted."""
        url = f"{self._base_url}/authorization/charge-session"
        headers = {
            "Authorization": self._token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {"Method": method, "Token": token}
        try:
            async with asyncio.timeout(API_TIMEOUT_SECONDS):
                async with self._session.post(
                    url, headers=headers, json=body
                ) as resp:
                    if resp.status == 202:
                        return
                    if resp.status == 401:
                        raise ChargePointAuthError(
                            "Unauthorized - check the API token"
                        )
                    if resp.status == 403:
                        raise ChargePointApiError(
                            "Forbidden - request not allowed in managed mode "
                            "or token not in the local list"
                        )
                    if resp.status == 429:
                        raise ChargePointRateLimitError("Rate limit exceeded")
                    try:
                        body_json = await resp.json()
                        msg = body_json.get("statusmsg", f"HTTP {resp.status}")
                    except (ValueError, ClientResponseError):
                        msg = f"HTTP {resp.status}"
                    raise ChargePointApiError(msg)
        except asyncio.TimeoutError as err:
            raise ChargePointConnectionError(
                f"Timeout talking to {self._host}"
            ) from err
        except ClientError as err:
            raise ChargePointConnectionError(str(err)) from err
