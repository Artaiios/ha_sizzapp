from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_SHARED_CODE
from . import SizzappCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Create multiple sensor entities
    entities = [
        SizzappSpeedSensor(coordinator, entry),
        SizzappLatitudeSensor(coordinator, entry),
        SizzappLongitudeSensor(coordinator, entry),
        SizzappInTripSensor(coordinator, entry),
        SizzappAngleSensor(coordinator, entry),
        SizzappNameSensor(coordinator, entry),
    ]
    
    async_add_entities(entities)


class SizzappBaseSensor(CoordinatorEntity[SizzappCoordinator], SensorEntity):
    """Base class for all Sizzapp sensors."""
    _attr_has_entity_name = True

    def __init__(self, coordinator: SizzappCoordinator, entry: ConfigEntry, sensor_type: str) -> None:
        super().__init__(coordinator)
        self._shared_code = entry.data[CONF_SHARED_CODE]
        self._sensor_type = sensor_type

        # Versuche unit_id als eindeutige ID zu verwenden, fallback auf shared_code
        unit_id = self._get_unit_id()
        base_unique = str(unit_id) if unit_id is not None else self._shared_code
        self._attr_unique_id = f"sizzapp_{sensor_type}_{base_unique}"

        # Name
        name = self._get_name()
        base_name = f"Sizzapp {name}" if name else f"Sizzapp {base_unique[:6]}…"
        self._attr_name = f"{base_name} {sensor_type.title()}"

    def _get_payload(self) -> dict[str, Any] | None:
        return self.coordinator.data

    def _get_unit_id(self) -> int | None:
        payload = self._get_payload()
        return int(payload["unit_id"]) if payload and "unit_id" in payload else None

    def _get_name(self) -> str | None:
        payload = self._get_payload()
        return str(payload["name"]).strip() if payload and "name" in payload else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        payload = self._get_payload()
        if not payload:
            return {"last_update_success": False}
        attrs = {
            "unit_id": payload.get("unit_id"),
            "name": payload.get("name"),
            "image_filename": payload.get("image_filename"),
            "dt_unit": payload.get("dt_unit"),
            "last_update_success": True,
        }
        return attrs


class SizzappSpeedSensor(SizzappBaseSensor):
    """Speed sensor in km/h."""
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator: SizzappCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "speed")

    @property
    def native_value(self) -> StateType:
        """Expose 'speed' as state (km/h)."""
        payload = self._get_payload()
        if not payload:
            return None
        try:
            return float(payload.get("speed", 0))
        except (TypeError, ValueError):
            return None


class SizzappLatitudeSensor(SizzappBaseSensor):
    """Latitude sensor."""
    _attr_icon = "mdi:latitude"

    def __init__(self, coordinator: SizzappCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "latitude")

    @property
    def native_value(self) -> StateType:
        """Expose 'lat' as state."""
        payload = self._get_payload()
        if not payload:
            return None
        try:
            return float(payload.get("lat", 0))
        except (TypeError, ValueError):
            return None


class SizzappLongitudeSensor(SizzappBaseSensor):
    """Longitude sensor."""
    _attr_icon = "mdi:longitude"

    def __init__(self, coordinator: SizzappCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "longitude")

    @property
    def native_value(self) -> StateType:
        """Expose 'lng' as state."""
        payload = self._get_payload()
        if not payload:
            return None
        try:
            return float(payload.get("lng", 0))
        except (TypeError, ValueError):
            return None


class SizzappInTripSensor(SizzappBaseSensor):
    """In trip status sensor."""
    _attr_icon = "mdi:car-traction-control"

    def __init__(self, coordinator: SizzappCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "in_trip")

    @property
    def native_value(self) -> StateType:
        """Expose 'in_trip' as state."""
        payload = self._get_payload()
        if not payload:
            return None
        return payload.get("in_trip", False)


class SizzappAngleSensor(SizzappBaseSensor):
    """Direction angle sensor."""
    _attr_icon = "mdi:compass"
    _attr_native_unit_of_measurement = "°"

    def __init__(self, coordinator: SizzappCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "angle")

    @property
    def native_value(self) -> StateType:
        """Expose 'angle' as state."""
        payload = self._get_payload()
        if not payload:
            return None
        try:
            return float(payload.get("angle", 0))
        except (TypeError, ValueError):
            return None


class SizzappNameSensor(SizzappBaseSensor):
    """Vehicle name sensor."""
    _attr_icon = "mdi:label"

    def __init__(self, coordinator: SizzappCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "name")

    @property
    def native_value(self) -> StateType:
        """Expose 'name' as state."""
        payload = self._get_payload()
        if not payload:
            return None
        name = payload.get("name")
        return str(name).strip() if name else None
