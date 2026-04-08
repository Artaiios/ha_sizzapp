from __future__ import annotations
from datetime import datetime, timezone, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_STALE_MINUTES, DEFAULT_STALE_MINUTES
from .coordinator import SizzappCoordinator
from .entity import SizzappBaseEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    code_hint = (getattr(coordinator, "name", None) or "sizzapp").removeprefix("sizzapp-")
    stale_minutes = entry.options.get(CONF_STALE_MINUTES, DEFAULT_STALE_MINUTES)

    entities: list[BinarySensorEntity] = []
    for unit_id, data in (coordinator.data or {}).items():
        name = (data.get("name") or f"Unit {unit_id}").strip()
        entities.append(SizzappTripSensor(coordinator, unit_id, name, code_hint))
        entities.append(SizzappStaleSensor(coordinator, unit_id, name, code_hint, stale_minutes))

    async_add_entities(entities)


class SizzappTripSensor(SizzappBaseEntity, BinarySensorEntity):
    _attr_name = "In Trip"
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_icon = "mdi:car"

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_in_trip"

    @property
    def is_on(self) -> bool | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        if not u:
            return None
        val = u.get("in_trip")
        if val is None:
            return None
        return bool(val)


class SizzappStaleSensor(SizzappBaseEntity, BinarySensorEntity):
    """Wird ON wenn der Tracker sich länger als X Minuten nicht gemeldet hat."""

    _attr_name = "Stale"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:clock-alert-outline"

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str, stale_minutes: int) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._stale_minutes = stale_minutes
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_stale"

    @property
    def is_on(self) -> bool | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        raw = u.get("dt_unit") or u.get("ts") or u.get("timestamp")
        if raw is None:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - dt
            return age > timedelta(minutes=self._stale_minutes)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict:
        return {"stale_threshold_minutes": self._stale_minutes}
