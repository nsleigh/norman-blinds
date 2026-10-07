"""Coordinator for Norman Blinds."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NormanBlindsApiClient, NormanBlindsAuthError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, LOGGER, MAX_TOLERATED_UPDATE_FAILURES


class NormanBlindsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage fetching data from the Norman gateway."""

    def __init__(self, hass: HomeAssistant, api: NormanBlindsApiClient) -> None:
        self.api = api
        self._consecutive_failures = 0
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN} coordinator",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""

        try:
            data = await self.api.async_get_combined_state()
        except NormanBlindsAuthError as err:
            raise ConfigEntryAuthFailed from err
        except Exception as err:  # pylint: disable=broad-except
            # The hub drops sessions and briefly 500s on login at scheduled times; ride
            # out a few short blips with the last known data rather than going unavailable.
            self._consecutive_failures += 1
            if self.data is not None and self._consecutive_failures <= MAX_TOLERATED_UPDATE_FAILURES:
                LOGGER.warning(
                    "Error fetching Norman hub data (failure %s/%s), keeping last known state: %s",
                    self._consecutive_failures,
                    MAX_TOLERATED_UPDATE_FAILURES,
                    err,
                )
                return self.data
            raise UpdateFailed(str(err)) from err

        self._consecutive_failures = 0
        data["gateway"] = self.api.gateway_info
        return data
