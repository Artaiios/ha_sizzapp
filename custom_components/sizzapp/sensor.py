from __future__ import annotations
from typing import Any
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass, UnitOfSpeed
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, CONF_SPEED_UNIT, DEFAULT_SPEED_UNIT
from .coordinator import SizzappCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SizzappCoordinator = hass.data[DOMAIN][entry.entry_id]
    speed_unit = entry.options.get(CONF_SPEED_UNIT, DEFAULT_SPEED_UNIT)
    code_hint = coordinator.name.removeprefix("sizzapp-")

    entities = []
    for unit_id, data in (coordinator.data or {}).items():
        name = (data.get("name") or f"Unit {unit_id}").strip()
        entities.append(SizzappSpeedSensor(coordinator, unit_id, name, speed_unit, code_hint))
        entities.append(SizzappTripSensor(coordinator, unit_id, name, code_hint))
        entities.append(SizzappHeadingSensor(coordinator, unit_id, name, code_hint))
    async_add_entities(entities)


def _kmh_to_mph(v: float) -> float:
    return v * 0.6213711922


class _BaseEntity(SensorEntity):
    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        self.coordinator = coordinator
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


class SizzappSpeedSensor(_BaseEntity):
    _attr_has_entity_name = True
    _attr_name = "Speed"
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, speed_unit: str, code_hint: str) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._speed_unit = speed_unit
        self._attr_unique_id = f"sizzapp_{code_hint}_{unit_id}_speed"

    @property
    def native_unit_of_measurement(self):
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


class SizzappHeadingSensor(_BaseEntity):
    _attr_has_entity_name = True
    _attr_name = "Heading"
    _attr_icon = "mdi:compass"

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator, unit_id, name, code_hint)
        self._attr_unique_id = f"sizzapp_{code_hint
