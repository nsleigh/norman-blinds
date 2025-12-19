"""Coordinator for Norman Blinds."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NormanBlindsApiClient, NormanBlindsApiError, NormanBlindsAuthError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, LOGGER


class NormanBlindsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage fetching data from the Norman gateway."""

    def __init__(self, hass: HomeAssistant, api: NormanBlindsApiClient) -> None:
        self.api = api
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN} coordinator",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""

        try:
            return await self.api.async_get_combined_state()
        except NormanBlindsAuthError as err:
            raise ConfigEntryAuthFailed from err
        except NormanBlindsApiError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:  # pylint: disable=broad-except
            raise UpdateFailed(str(err)) from err