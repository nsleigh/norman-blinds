"""Diagnostic sensors for Norman Blinds."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NormanBlindsDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Norman Blinds diagnostic sensors."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: NormanBlindsDataUpdateCoordinator = data["coordinator"]

    entities: list[SensorEntity] = [NormanBatteryCheckSensor(coordinator)]

    def _build_entities() -> list[SensorEntity]:
        local_entities: list[SensorEntity] = []
        for item in coordinator.data.get("windows", []):
            window = item.get("window") or {}
            room = item.get("room") or {}
            suggested_area = item.get("suggested_area") or room.get("Name")
            local_entities.extend(create_window_sensors(coordinator, window, suggested_area))
        return local_entities

    # Initial batch from current data
    entities.extend(_build_entities())
    async_add_entities(entities)

    seen_ids: set[str] = {entity.unique_id for entity in entities if entity.unique_id}

    async def _async_add_new_entities() -> None:
        new_entities = _build_entities()
        to_add = [
            entity for entity in new_entities if entity.unique_id and entity.unique_id not in seen_ids
        ]
        if to_add:
            seen_ids.update(entity.unique_id for entity in to_add if entity.unique_id)
            async_add_entities(to_add)

    def _handle_coordinator_update() -> None:
        coordinator.hass.async_create_task(_async_add_new_entities())

    coordinator.async_add_listener(_handle_coordinator_update)


class NormanBatteryCheckSensor(CoordinatorEntity[NormanBlindsDataUpdateCoordinator], SensorEntity):
    """Sensor exposing the gateway battery check status."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Battery Check"
    _attr_icon = "mdi:battery-check"

    def __init__(self, coordinator: NormanBlindsDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "norman_blinds_battery_check"

    @property
    def native_value(self) -> Any:
        """Return the battery check result."""

        value = self.coordinator.data.get("battery_check")
        if isinstance(value, dict):
            return value.get("check_battery") or value.get("status") or value
        return value

    @property
    def available(self) -> bool:
        """Available when coordinator has data."""

        return self.coordinator.last_update_success

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for the hub."""

        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": "Norman Gateway",
            "manufacturer": "Norman",
        }


WINDOW_SENSORS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        key="battery",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="Rssi",
        name="Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="temp",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="position",
        name="Position",
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="solar",
        name="Solar",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="usb",
        name="USB Power",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ver",
        name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
]


def create_window_sensors(
    coordinator: NormanBlindsDataUpdateCoordinator, window: dict[str, Any], room_name: str | None
) -> list[SensorEntity]:
    """Create sensors for a single window."""

    window_id = window.get("Id") or window.get("id")
    window_name = window.get("Name") or (f"Blind {window_id}" if window_id else "Blind")
    device_name = f"{room_name} - {window_name}" if room_name else window_name
    identifiers = {(DOMAIN, f"window_{window_id}")} if window_id is not None else {(DOMAIN, device_name)}

    device_info = {
        "identifiers": identifiers,
        "name": device_name,
        "manufacturer": "Norman",
        "via_device": (DOMAIN, "hub"),
    }

    sensors: list[SensorEntity] = []
    for desc in WINDOW_SENSORS:
        value = window.get(desc.key)
        if value is None and desc.key.lower() != desc.key:
            # Try lowercase key if original case not present
            value = window.get(desc.key.lower())
        if value is None:
            continue
        entity = NormanWindowSensor(
            coordinator=coordinator,
            window_id=window_id,
            device_info=device_info,
            room_name=room_name,
            window_name=window_name,
            description=desc,
        )
        sensors.append(entity)

    return sensors


class NormanWindowSensor(CoordinatorEntity[NormanBlindsDataUpdateCoordinator], SensorEntity):
    """Sensor representing a window attribute."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: NormanBlindsDataUpdateCoordinator,
        window_id: Any,
        device_info: dict[str, Any],
        room_name: str | None,
        window_name: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._window_id = window_id
        self._device_info = device_info
        self.entity_description = description
        metric = description.name
        base = f"{room_name} - {window_name}" if room_name else window_name
        self._attr_name = f"{base} {metric}"
        self._attr_unique_id = f"{window_id}_{description.key}" if window_id is not None else f"{base}_{description.key}"
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_device_class = description.device_class
        self._attr_entity_category = description.entity_category

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for this window."""

        return self._device_info

    @property
    def native_value(self) -> Any:
        """Return the current value from coordinator data."""

        windows = self.coordinator.data.get("windows", [])
        for item in windows:
            window = item.get("window") or {}
            if (window.get("Id") or window.get("id")) == self._window_id:
                return window.get(self.entity_description.key)
        return None
