"""Button platform for Norman Blinds room presets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .coordinator import NormanBlindsDataUpdateCoordinator

PRESET_BUTTONS: list[ButtonEntityDescription] = [
    ButtonEntityDescription(key="view", translation_key="view"),
    ButtonEntityDescription(key="privacy", translation_key="privacy"),
    ButtonEntityDescription(key="favorite", translation_key="favorite"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Norman Blinds preset buttons."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: NormanBlindsDataUpdateCoordinator = data["coordinator"]

    entities: list[ButtonEntity] = []

    def _build_entities() -> list[ButtonEntity]:
        local_entities: list[ButtonEntity] = []

        # Prefer explicit room list; fall back to deriving rooms from window payloads.
        rooms = coordinator.data.get("rooms") or []
        if not rooms:
            # Derive unique rooms from windows.
            seen: dict[Any, dict[str, Any]] = {}
            for item in coordinator.data.get("windows", []):
                window = item.get("window") or {}
                rid = (
                    window.get("roomId")
                    or window.get("room_id")
                    or window.get("room")
                    or window.get("RId")
                )
                if rid is None or rid in seen:
                    continue
                seen[rid] = {
                    "Id": rid,
                    "Name": item.get("suggested_area") or window.get("roomName"),
                }
            rooms = list(seen.values())
            LOGGER.debug("Derived rooms from windows for preset buttons: %s", rooms)
        else:
            LOGGER.debug("Using coordinator rooms for preset buttons: %s", rooms)

        for room in rooms:
            room_id = room.get("Id") or room.get("id") or room.get("roomId")
            room_name = room.get("Name") or room.get("name") or room.get("roomName")
            for desc in PRESET_BUTTONS:
                local_entities.append(
                    NormanBlindsRoomPresetButton(
                        coordinator=coordinator,
                        room_id=room_id,
                        room_name=room_name,
                        description=desc,
                    )
                )
        return local_entities

    entities.extend(_build_entities())
    if entities:
        LOGGER.debug("Initial preset button entities: %s", [e.unique_id for e in entities])
    async_add_entities(entities)

    seen_ids: set[str] = {entity.unique_id for entity in entities if entity.unique_id}

    async def _async_add_new_entities() -> None:
        new_entities = _build_entities()
        to_add = [
            entity
            for entity in new_entities
            if entity.unique_id and entity.unique_id not in seen_ids
        ]
        if not to_add:
            return

        seen_ids.update(entity.unique_id for entity in to_add if entity.unique_id)
        LOGGER.debug("Adding new preset button entities: %s", [e.unique_id for e in to_add])
        async_add_entities(to_add)

    def _handle_coordinator_update() -> None:
        coordinator.hass.async_create_task(_async_add_new_entities())

    coordinator.async_add_listener(_handle_coordinator_update)


class NormanBlindsRoomPresetButton(
    CoordinatorEntity[NormanBlindsDataUpdateCoordinator], ButtonEntity
):
    """Button to trigger a preset on all blinds in a room."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: NormanBlindsDataUpdateCoordinator,
        room_id: Any,
        room_name: str | None,
        description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._room_id = room_id
        self._room_name = room_name or "Room"
        label = (
            description.name
            or description.translation_key
            or description.key
        )
        self._attr_name = f"{self._room_name} {label}"
        suffix = description.key
        base_id = self._room_id if self._room_id is not None else self._room_name
        self._attr_unique_id = f"room_{base_id}_preset_{suffix}"
        gateway = coordinator.data.get("gateway") or {}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "hub")},
            "name": gateway.get("hubName") or "Norman Gateway",
            "manufacturer": "Norman",
            "sw_version": gateway.get("swVer"),
        }

    @property
    def available(self) -> bool:
        """Combine coordinator availability with presence of the room."""

        rooms = self.coordinator.data.get("rooms") or []
        room_present = any(
            (room.get("Id") or room.get("id") or room.get("roomId")) == self._room_id
            for room in rooms
        )
        if not room_present:
            for item in self.coordinator.data.get("windows", []):
                window = item.get("window") or {}
                rid = (
                    window.get("roomId")
                    or window.get("room_id")
                    or window.get("room")
                    or window.get("RId")
                )
                if rid == self._room_id:
                    room_present = True
                    break
        return room_present and bool(self.coordinator.last_update_success)

    async def async_press(self, **kwargs: Any) -> None:
        """Handle the button press."""

        if self._room_id is None:
            return
        await self.coordinator.api.async_set_room_preset(
            self._room_id, self.entity_description.key
        )
