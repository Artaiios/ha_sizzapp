from __future__ import annotations
from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_COORD_PRECISION, DEFAULT_COORD_PRECISION, IMAGE_BASE_URL
from .coordinator import SizzappCoordinator
from .entity import SizzappBaseEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    code_hint = (getattr(coordinator, "name", None) or "sizzapp").removeprefix("sizzapp-")
    coord_precision = entry.options.get(CONF_COORD_PRECISION, DEFAULT_COORD_PRECISION)

    entities: list[SizzappLocationTracker] = []
    for unit_id, data in (coordinator.data or {}).items():
        name = (data.get("name") or f"Unit {unit_id}").strip()
        entities.append(SizzappLocationTracker(coordinator, unit_id, name, code_hint, coord_precision))

    async_add_entities(entities)


class SizzappLocationTracker(SizzappBaseEntity, TrackerEntity):
    """GPS-Tracker-Entität für Sizzapp-Geräte."""

    _attr_name = "Location"
    _attr_icon = "mdi:map-marker"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str, coord_precision: int) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._coord_precision = coord_precision
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_location"

        # Tracker-Bild als entity_picture
        image_filename = (coordinator.data or {}).get(unit_id, {}).get("image_filename")
        if image_filename:
            self._attr_entity_picture = f"{IMAGE_BASE_URL}{image_filename}"

    def _round(self, val: float | None) -> float | None:
        if val is None:
            return None
        return round(val, int(self._coord_precision))

    @property
    def latitude(self) -> float | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        lat = u.get("lat") or u.get("latitude")
        try:
            return self._round(float(lat)) if lat is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def longitude(self) -> float | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        lon = u.get("lon") or u.get("lng") or u.get("longitude")
        try:
            return self._round(float(lon)) if lon is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def location_accuracy(self) -> int:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        acc = u.get("accuracy") or u.get("hdop") or u.get("radius")
        try:
            return max(0, int(round(float(acc)))) if acc is not None else 0
        except (TypeError, ValueError):
            return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        return {
            "speed_kmh": u.get("speed"),
            "course": u.get("angle"),
            "in_trip": u.get("in_trip"),
            "last_update": u.get("dt_unit") or u.get("ts") or u.get("timestamp"),
        }
