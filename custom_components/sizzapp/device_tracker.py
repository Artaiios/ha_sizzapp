# custom_components/sizzapp/device_tracker.py
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SizzappCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Sizzapp device trackers from a config entry."""
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    code_hint = (getattr(coordinator, "name", None) or "sizzapp").removeprefix("sizzapp-")

    entities: list[SizzappLocationTracker] = []
    for unit_id, data in (coordinator.data or {}).items():
        name = (data.get("name") or f"Unit {unit_id}").strip()
        entities.append(SizzappLocationTracker(coordinator, unit_id, name, code_hint))

    async_add_entities(entities)


class SizzappLocationTracker(CoordinatorEntity[SizzappCoordinator], TrackerEntity):
    """GPS-Tracker-Entität für Sizzapp-Geräte."""

    _attr_has_entity_name = True
    _attr_name = "Location"  # wird in DE als „Standort“ angezeigt
    _attr_icon = "mdi:map-marker"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator)
        self._unit_id = unit_id
        self._devname = name
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_location"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(unit_id))},
            manufacturer=MANUFACTURER,
            name=name,
            model="Tracker",
        )

    @property
    def available(self) -> bool:
        """Nur verfügbar, wenn der letzte Abruf ok war und wir Daten für die Unit haben."""
        return self.coordinator.last_update_success and self._unit_id in (self.coordinator.data or {})

    # ---- Pflichtfelder für TrackerEntity ----
    @property
    def latitude(self) -> float | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        lat = u.get("lat") or u.get("latitude")
        try:
            return float(lat) if lat is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def longitude(self) -> float | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        lon = u.get("lon") or u.get("lng") or u.get("longitude")
        try:
            return float(lon) if lon is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def location_accuracy(self) -> int:
        """MUSS eine Zahl liefern (Meter). Nie None zurückgeben."""
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        acc = u.get("accuracy") or u.get("hdop") or u.get("radius")
        try:
            return max(0, int(round(float(acc)))) if acc is not None else 0
        except (TypeError, ValueError):
            return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute, rein informativ."""
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        return {
            "speed_kmh": u.get("speed"),
            "course": u.get("angle"),
            "in_trip": u.get("in_trip"),
            "last_update": u.get("dt_unit") or u.get("ts") or u.get("timestamp"),
        }
