from __future__ import annotations
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SizzappCoordinator


class _BaseEntity(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator)
        self._unit_id = unit_id
        self._devname = name
        self._code_hint = code_hint
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(unit_id))},
            manufacturer=MANUFACTURER,
            name=name,
            model="Tracker",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._unit_id in (self.coordinator.data or {})


class SizzappTripSensor(_BaseEntity):
    _attr_has_entity_name = True
    _attr_name = "In Trip"
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_icon = "mdi:car"

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_in_trip"

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        
        u = self.coordinator.data.get(self._unit_id, {})
        if not u:
            return None
            
        val = u.get("in_trip")
        if val is None:
            return None
            
        # API returns in_trip as boolean (true/false), use it directly
        # but ensure it's a proper boolean for Home Assistant
        if isinstance(val, bool):
            return val
        else:
            # Fallback: convert to boolean if it's not already
            return bool(val)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    code_hint = (getattr(coordinator, "name", None) or "sizzapp").removeprefix("sizzapp-")

    entities: list[BinarySensorEntity] = []
    for unit_id, data in (coordinator.data or {}).items():
        name = (data.get("name") or f"Unit {unit_id}").strip()
        entities.append(SizzappTripSensor(coordinator, unit_id, name, code_hint))
    
    async_add_entities(entities)
