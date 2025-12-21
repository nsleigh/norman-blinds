"""Cover platform for Norman Blinds."""
from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverDeviceClass, CoverEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_VIA_DEVICE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NormanBlindsDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Norman Blinds cover entities from config entry."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: NormanBlindsDataUpdateCoordinator = data["coordinator"]

    entities: list[NormanBlindsCover] = []
    for item in coordinator.data.get("windows", []):
        window = item.get("window") or {}
        room = item.get("room") or {}
        suggested_area = item.get("suggested_area") or room.get("Name")

        entity = NormanBlindsCover(coordinator, window, suggested_area)
        entities.append(entity)

    async_add_entities(entities)


class NormanBlindsCover(CoordinatorEntity[NormanBlindsDataUpdateCoordinator], CoverEntity):
    """Representation of a Norman blind."""

    _attr_should_poll = False
    _attr_supported_features = 0
    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_has_entity_name = False
    _attr_is_closed: bool | None = None
    _attr_current_cover_position: int | None = None
    _attr_available = False

    def __init__(
        self,
        coordinator: NormanBlindsDataUpdateCoordinator,
        window: dict[str, Any],
        suggested_area: str | None,
        ) -> None:
        """Initialize the cover entity."""

        super().__init__(coordinator)
        self._window_id: int | str | None = window.get("Id") or window.get("id")
        self._room_name: str | None = suggested_area
        self._window_name: str | None = window.get("Name")
        self._attr_unique_id = str(self._window_id) if self._window_id is not None else None
        if self._room_name and self._window_name:
            self._attr_name = f"{self._room_name} - {self._window_name}"
        elif self._window_name:
            self._attr_name = self._window_name
        elif self._room_name and self._window_id is not None:
            self._attr_name = f"{self._room_name} - Blind {self._window_id}"
        elif self._window_id is not None:
            self._attr_name = f"Blind {self._window_id}"
        else:
            self._attr_name = "Blind"
        if suggested_area:
            self._attr_suggested_area = suggested_area
        device_name = self._attr_name if self._room_name else (self._window_name or "Norman Blind")
        self._device_info = {
            "identifiers": {(DOMAIN, f"window_{self._window_id}")} if self._window_id is not None else {(DOMAIN, f"window_{self._attr_name}")},
            "name": device_name,
            "manufacturer": "Norman",
            ATTR_VIA_DEVICE: (DOMAIN, "hub"),
        }

        self._attr_current_cover_position: int | None = None
        self._attr_is_closed: bool | None = None
        self._update_from_window(window)
        self._attr_available = self._window_id is not None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for the hub."""

        return self._device_info

    @property
    def available(self) -> bool:
        """Combine coordinator availability with local flag."""

        return bool(self._attr_available) and bool(self.coordinator.last_update_success)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        windows = self.coordinator.data.get("windows", [])
        for item in windows:
            window = item.get("window") or {}
            if (window.get("Id") or window.get("id")) == self._window_id:
                self._update_from_window(window)
                self._attr_available = True
                break
        else:
            self._attr_available = False

        self.async_write_ha_state()

    @property
    def is_closed(self) -> bool | None:  # type: ignore[override]
        """Return if the cover is closed."""

        # Guard against missing attribute initialization
        return getattr(self, "_attr_is_closed", None)

    def _update_from_window(self, window: dict[str, Any]) -> None:
        """Update internal state from window payload."""

        position = window.get("position")
        if isinstance(position, (int, float)):
            self._attr_current_cover_position = int(position)
            pos_int = int(position)
            # Treat only 100 as closed; all other values are considered open.
            self._attr_is_closed = pos_int == 100
        else:
            self._attr_current_cover_position = None
            self._attr_is_closed = None

        # Attributes are exposed as dedicated sensors.

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Not supported by the local gateway."""

        raise NotImplementedError("Setting cover position is not supported for Norman blinds")

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Not supported by the local gateway."""

        raise NotImplementedError("Opening cover is not supported for Norman blinds")

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Not supported by the local gateway."""

        raise NotImplementedError("Closing cover is not supported for Norman blinds")

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Not supported by the local gateway."""

        raise NotImplementedError("Stopping cover is not supported for Norman blinds")
