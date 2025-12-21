"""Cover platform for Norman Blinds."""
from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverDeviceClass, CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_VIA_DEVICE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ALLOWED_POSITIONS, DOMAIN, LOGGER
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
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
    )
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
            closed_percent = int(position)
            open_percent = max(0, min(100, 100 - closed_percent))
            self._attr_current_cover_position = open_percent
            self._attr_is_closed = open_percent == 0
        else:
            self._attr_current_cover_position = None
            self._attr_is_closed = None

        # Attributes are exposed as dedicated sensors.

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set cover position (0-100 open) to the closest supported device value."""

        position = kwargs.get("position")
        if position is None:
            return

        target = self._normalize_position(int(position))
        await self._send_position_command(target)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""

        # Prefer a 63% closed position when opening, snapped to the nearest supported value.
        target = min(ALLOWED_POSITIONS, key=lambda value: abs(value - 63))
        await self._send_position_command(target)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""

        await self._send_position_command(self._normalize_position(0))

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Not supported by the local gateway."""

        raise NotImplementedError("Stopping cover is not supported for Norman blinds")

    def _normalize_position(self, requested: int) -> int:
        """Clamp and map requested open percentage to nearest supported closed percentage."""

        clamped_open = max(0, min(100, requested))
        target_closed = 100 - clamped_open
        nearest = min(ALLOWED_POSITIONS, key=lambda value: abs(value - target_closed))
        if nearest != target_closed:
            LOGGER.debug(
                "Adjusting requested position %s%% open to supported %s%% closed for blind %s",
                clamped_open,
                nearest,
                self._window_id,
            )
        return nearest

    async def _send_position_command(self, target: int) -> None:
        """Send a device position command to the gateway and refresh state."""

        if self._window_id is None:
            LOGGER.warning("Cannot set position; missing window id for %s", self.name)
            return

        await self.coordinator.api.async_set_window_position(self._window_id, target)
        open_percent = max(0, min(100, 100 - target))
        self._attr_current_cover_position = open_percent
        self._attr_is_closed = open_percent == 0
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
