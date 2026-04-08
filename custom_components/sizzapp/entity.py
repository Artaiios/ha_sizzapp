from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, IMAGE_BASE_URL
from .coordinator import SizzappCoordinator


class SizzappBaseEntity(CoordinatorEntity[SizzappCoordinator]):
    """Gemeinsame Basis für alle Sizzapp-Entitäten."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SizzappCoordinator, unit_id: int, name: str, code_hint: str) -> None:
        super().__init__(coordinator)
        self._unit_id = unit_id
        self._devname = name
        self._code_hint = code_hint

        # Bild aus der API (falls vorhanden)
        image_filename = (coordinator.data or {}).get(unit_id, {}).get("image_filename")
        entity_picture = f"{IMAGE_BASE_URL}{image_filename}" if image_filename else None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(unit_id))},
            manufacturer=MANUFACTURER,
            name=name,
            model="Tracker",
            configuration_url="https://www.sizzapp.com",
        )
        if entity_picture:
            self._attr_device_info["entity_picture"] = entity_picture

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._unit_id in (self.coordinator.data or {})
