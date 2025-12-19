"""API client for the Norman Blinds gateway."""
from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientSession

from .const import DEFAULT_APP_VERSION, LOGGER, LOGIN_ENDPOINT, ROOM_INFO_ENDPOINT, WINDOW_INFO_ENDPOINT


class NormanBlindsApiError(Exception):
    """Base class for Norman Blinds errors."""


class NormanBlindsAuthError(NormanBlindsApiError):
    """Raised when authentication fails."""


class NormanBlindsApiClient:
    """Thin async client for the local Norman gateway."""

    def __init__(self, session: ClientSession, host: str, password: str) -> None:
        self._session = session
        self._host = host.rstrip("/")
        self._password = password
        self._login_lock = asyncio.Lock()
        self._logged_in = False
        self._app_version = DEFAULT_APP_VERSION

    @property
    def base_url(self) -> str:
        """Return the base URL for the gateway, defaulting to http."""

        if self._host.startswith("http://") or self._host.startswith("https://"):
            return self._host
        return f"http://{self._host}"

    def _build_url(self, endpoint: str) -> str:
        """Return a full URL for the provided endpoint."""

        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        if endpoint.startswith("/"):
            return f"{self.base_url}{endpoint}"
        return f"{self.base_url}/{endpoint}"

    async def _login(self, *, force: bool = False) -> None:
        """Authenticate and persist cookies for subsequent requests."""

        async with self._login_lock:
            if self._logged_in and not force:
                return

            url = self._build_url(LOGIN_ENDPOINT)
            payload: dict[str, Any] = {"password": self._password, "app_version": self._app_version}
            masked_payload = {**payload, "password": "***"}
            LOGGER.debug("Posting login payload to %s: %s", url, masked_payload)

            async with self._session.post(url, json=payload) as response:
                if response.status in (401, 403):
                    raise NormanBlindsAuthError("Invalid credentials for Norman gateway")
                response.raise_for_status()
                login_body = await response.text()
                LOGGER.debug(
                    "Login response status: %s, headers: %s, body: %s",
                    response.status,
                    dict(response.headers),
                    login_body,
                )
                login_data: Any | None = None
                try:
                    login_data = await response.json(content_type=None)
                except Exception:  # pylint: disable=broad-except
                    login_data = None

                if isinstance(login_data, dict):
                    error_code = login_data.get("errorCode", 0)
                    if error_code not in (None, 0, "0"):
                        raise NormanBlindsAuthError(f"Login failed, errorCode: {error_code}")

                self._logged_in = True
                LOGGER.debug(
                    "Login succeeded with app_version %s, session cookie jar keys: %s",
                    self._app_version,
                    list(response.cookies.keys()),
                )

    async def _ensure_login(self) -> None:
        """Log in if we do not already have cookies."""

        if not self._logged_in:
            await self._login()

    async def _request(
        self,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        *,
        allow_reauth: bool = True,
    ) -> Any:
        """POST to the gateway, refreshing authentication on 401."""

        await self._ensure_login()
        url = self._build_url(endpoint)
        LOGGER.debug(
            "Posting to %s with payload %s",
            url,
            payload or {},
        )

        async with self._session.post(url, json=payload or {}) as response:
            body_text = await response.text()
            LOGGER.debug(
                "Response status for %s: %s, headers: %s, body: %s",
                endpoint,
                response.status,
                dict(response.headers),
                body_text,
            )
            if response.status == 401:
                LOGGER.info("Session expired, retrying login")
                if not allow_reauth:
                    raise NormanBlindsAuthError("Authentication failed after retry")
                await self._login(force=True)
                return await self._request(endpoint, payload, allow_reauth=False)

            response.raise_for_status()
            data = await response.json(content_type=None)
            LOGGER.debug("Received response from %s: %s", endpoint, data)
            return data

    async def async_get_room_info(self) -> list[dict[str, Any]]:
        """Return rooms from the gateway."""

        payload = await self._request(ROOM_INFO_ENDPOINT)
        if isinstance(payload, dict):
            rooms = payload.get("rooms")
        else:
            rooms = payload

        if not isinstance(rooms, list):
            LOGGER.debug("Unexpected room payload: %s", payload)
            raise NormanBlindsApiError("Malformed room data from gateway")
        return rooms

    async def async_get_window_info(self) -> list[dict[str, Any]]:
        """Return windows from the gateway."""

        payload = await self._request(WINDOW_INFO_ENDPOINT)
        if isinstance(payload, dict):
            windows = payload.get("windows")
        else:
            windows = payload

        if not isinstance(windows, list):
            LOGGER.debug("Unexpected window payload: %s", payload)
            raise NormanBlindsApiError("Malformed window data from gateway")
        return windows

    async def async_get_combined_state(self) -> dict[str, Any]:
        """Return windows merged with their rooms and suggested areas."""

        rooms = await self.async_get_room_info()
        windows = await self.async_get_window_info()

        room_index = {
            room.get("roomId") or room.get("id") or room.get("Id"): room for room in rooms
        }
        combined: list[dict[str, Any]] = []

        for window in windows:
            room_id = (
                window.get("roomId")
                or window.get("room_id")
                or window.get("room")
                or window.get("RId")
            )
            room = room_index.get(room_id)
            suggested_area = (
                room.get("roomName") or room.get("name") or room.get("Name") if room else None
            )

            combined.append(
                {
                    "window": window,
                    "room": room,
                    "room_name": suggested_area,
                    "suggested_area": suggested_area,
                }
            )

        return {"rooms": rooms, "windows": combined}
