from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfSpeed

from .const import DOMAIN, CONF_SPEED_UNIT, DEFAULT_SPEED_UNIT
from .coordinator import SizzappCoordinator
from .entity import SizzappBaseEntity


def _kmh_to_mph(v: float) -> float:
    return v * 0.6213711922


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    speed_unit = entry.options.get(CONF_SPEED_UNIT, DEFAULT_SPEED_UNIT)
    code_hint = (getattr(coordinator, "name", None) or "sizzapp").removeprefix("sizzapp-")

    entities: list[SensorEntity] = []
    for unit_id, data in (coordinator.data or {}).items():
        name = (data.get("name") or f"Unit {unit_id}").strip()
        entities.append(SizzappSpeedSensor(coordinator, unit_id, name, speed_unit, code_hint))
        entities.append(SizzappHeadingSensor(coordinator, unit_id, name, code_hint))
        entities.append(SizzappLastUpdateSensor(coordinator, unit_id, name, code_hint))
    async_add_entities(entities)


class SizzappSpeedSensor(SizzappBaseEntity, SensorEntity):
    _attr_name = "Speed"
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, speed_unit: str, code_hint: str) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._speed_unit = speed_unit
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_speed"

    @property
    def native_unit_of_measurement(self) -> str:
        return UnitOfSpeed.MILES_PER_HOUR if self._speed_unit == "mph" else UnitOfSpeed.KILOMETERS_PER_HOUR

    @property
    def native_value(self) -> float | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        spd = u.get("speed")
        if spd is None:
            return None
        try:
            v = float(spd)
        except (TypeError, ValueError):
            return None
        return round(_kmh_to_mph(v), 1) if self._speed_unit == "mph" else round(v, 1)


class SizzappHeadingSensor(SizzappBaseEntity, SensorEntity):
    _attr_name = "Heading"
    _attr_icon = "mdi:compass"
    _attr_native_unit_of_measurement = "°"

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_heading"

    @property
    def native_value(self) -> int | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        ang = u.get("angle")
        try:
            return int(ang) if ang is not None else None
        except (TypeError, ValueError):
            return None


class SizzappLastUpdateSensor(SizzappBaseEntity, SensorEntity):
    """Zeitpunkt des letzten Tracker-Updates (dt_unit aus der API)."""

    _attr_name = "Last Update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_last_update"

    @property
    def native_value(self) -> datetime | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        raw = u.get("dt_unit") or u.get("ts") or u.get("timestamp")
        if raw is None:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None
