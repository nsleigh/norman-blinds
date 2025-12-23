"""The Norman Blinds integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NormanBlindsApiClient
from .const import CONF_HOST, CONF_PASSWORD, DEFAULT_PASSWORD, DOMAIN
from .coordinator import NormanBlindsDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.COVER, Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Norman Blinds from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    api = NormanBlindsApiClient(
        session,
        entry.data[CONF_HOST],
        entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
    )

    coordinator = NormanBlindsDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
