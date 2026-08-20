"""The Norman Blinds integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
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


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow removing a device the gateway no longer reports.

    Windows/rooms the hub last reported are still "live" and must not be
    removable through the UI; anything else (e.g. a blind that has been
    physically taken off the gateway) is safe to drop from the registry.
    """

    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data is None:
        return True

    coordinator: NormanBlindsDataUpdateCoordinator = data["coordinator"]
    known_ids = {(DOMAIN, "hub")}
    for item in coordinator.data.get("windows", []):
        window = item.get("window") or {}
        window_id = window.get("Id") or window.get("id")
        if window_id is not None:
            known_ids.add((DOMAIN, f"window_{window_id}"))

    return device_entry.identifiers.isdisjoint(known_ids)
