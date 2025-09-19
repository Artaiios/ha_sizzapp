from __future__ import annotations
from typing import Any
from datetime import datetime, timezone, timedelta
import dateutil.parser
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, CONF_COORD_PRECISION, DEFAULT_COORD_PRECISION
from .coordinator import SizzappCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    precision = entry.options.get(CONF_COORD_PRECISION, DEFAULT_COORD_PRECISION)

    entities = []
    for unit_id, data in (coordinator.data or {}).items():
        entities.append(SizzappTracker(coordinator, unit_id, data, precision))
    async_add_entities(entities)


class SizzappTracker(TrackerEntity):
    _attr_has_entity_name = True
    _attr_name = "Location"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, data: dict[str, Any], precision: int) -> None:
        self.coordinator = coordinator
        self._unit_id = unit_id
        self._precision = int(max(0, min(6, precision)))
        self._device_name = (data.get("name") or f"Unit {unit_id}").strip()

        code_hint = coordinator.name.removeprefix("sizzapp-")
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_tracker"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(unit_id))},
            manufacturer=MANUFACTURER,
            name=self._device_name,
            model="Tracker",
        )

    @property
    def available(self) -> bool:
        if not (self.coordinator.last_update_success and self._unit_id in (self.coordinator.data or {})):
            return False
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        ts = u.get("dt_unit")
        if not ts:
            return True
        try:
            dt = dateutil.parser.isoparse(ts).astimezone(timezone.utc)
            return (datetime.now(timezone.utc) - dt) < timedelta(minutes=15)
        except Exception:
            return True

    @property
    def latitude(self) -> float | None:
        u = (self.coordinator.data or {}).get(self._unit_id)
        if not u:
            return None
        lat = u.get("lat")
        if lat is None:
            return None
        return round(float(lat), self._precision)

    @property
    def longitude(self) -> float | None:
        u = (self.coordinator.data or {}).get(self._unit_id)
        if not u:
            return None
        lng = u.get("lng")
        if lng is None:
            return None
        return round(float(lng), self._precision)

    @property
    def location_accuracy(self) -> int | None:
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        return {
            "unit_id": self._unit_id,
            "name": u.get("name"),
            "speed_kmh": u.get("speed"),
            "heading": u.get("angle"),
            "in_trip": u.get("in_trip"),
            "last_update_utc": u.get("dt_unit"),
            "image_filename": u.get("image_filename"),
        }

    async def async_update(self) -> None:
        return

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
