from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SizzappCoordinator


class SizzappBaseEntity(CoordinatorEntity[SizzappCoordinator]):
    """Gemeinsame Basis für alle Sizzapp-Entitäten."""

    _attr_has_entity_name = True

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
            configuration_url="https://www.sizzapp.com",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._unit_id in (self.coordinator.data or {})
