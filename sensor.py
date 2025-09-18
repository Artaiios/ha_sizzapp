from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_SHARED_CODE
from . import SizzappCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SizzappSensor(coordinator, entry)])


class SizzappSensor(CoordinatorEntity[SizzappCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_icon = "mdi:car"

    def __init__(self, coordinator: SizzappCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._shared_code = entry.data[CONF_SHARED_CODE]

        # Versuche unit_id als eindeutige ID zu verwenden, fallback auf shared_code
        unit_id = self._get_unit_id()
        base_unique = str(unit_id) if unit_id is not None else self._shared_code
        self._attr_unique_id = f"sizzapp_{base_unique}"

        # Name
        name = self._get_name()
        self._attr_name = f"Sizzapp {name}" if name else f"Sizzapp {base_unique[:6]}…"

    def _get_payload(self) -> dict[str, Any] | None:
        return self.coordinator.data

    def _get_unit_id(self) -> int | None:
        payload = self._get_payload()
        return int(payload["unit_id"]) if payload and "unit_id" in payload else None

    def _get_name(self) -> str | None:
        payload = self._get_payload()
        return str(payload["name"]).strip() if payload and "name" in payload else None

    @property
    def native_value(self) -> StateType:
        """Expose 'speed' as state (km/h)."""
        payload = self._get_payload()
        if not payload:
            return None
        # speed kann 0 sein (valide)
        try:
            return float(payload.get("speed", 0))
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        payload = self._get_payload()
        if not payload:
            return {"last_update_success": False}
        attrs = {
            "unit_id": payload.get("unit_id"),
            "name": payload.get("name"),
            "image_filename": payload.get("image_filename"),
            "speed": payload.get("speed"),
            "dt_unit": payload.get("dt_unit"),
            "lat": payload.get("lat"),
            "lng": payload.get("lng"),
            "angle": payload.get("angle"),
            "in_trip": payload.get("in_trip"),
            "last_update_success": True,
        }
        return attrs
