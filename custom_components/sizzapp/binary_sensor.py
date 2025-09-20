# custom_components/sizzapp/binary_sensor.py
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
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
    """Set up Sizzapp binary sensors from a config entry."""
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    code_hint = (getattr(coordinator, "name", None) or "sizzapp").removeprefix("sizzapp-")

    entities: list[SizzappTripBinary] = []
    for unit_id, data in (coordinator.data or {}).items():
        name = (data.get("name") or f"Unit {unit_id}").strip()
        entities.append(SizzappTripBinary(coordinator, unit_id, name, code_hint))

    async_add_entities(entities)


class SizzappTripBinary(CoordinatorEntity[SizzappCoordinator], BinarySensorEntity):
    """Zeigt an, ob das Fahrzeug in einer Fahrt ist."""

    _attr_has_entity_name = True
    _attr_name = "In Trip"
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_icon = "mdi:car"

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator)
        self._unit_id = unit_id
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_in_trip"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(unit_id))},
            manufacturer=MANUFACTURER,
            name=name,
            model="Tracker",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._unit_id in (self.coordinator.data or {})

    @property
    def is_on(self) -> bool | None:
        u = (self.coordinator.data or {}).get(self._unit_id, {})
        # Deine Diagnose zeigt "in_trip": false  -> genau dieses Feld verwenden
        val = u.get("in_trip")
        if val is None:
            return None
        # falls API mal "0"/"1" als String liefert:
        if isinstance(val, str):
            val = val.strip().lower()
            if val in ("1", "true", "yes", "y"):
                return True
            if val in ("0", "false", "no", "n"):
                return False
            return None
        return bool(val)
