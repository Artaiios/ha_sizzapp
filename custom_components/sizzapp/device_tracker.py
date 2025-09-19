from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, MANUFACTURER

class SizzappTracker(TrackerEntity):
    _attr_has_entity_name = True
    _attr_name = "Location"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator, unique, device_name):
        self.coordinator = coordinator
        self._attr_unique_id = f"{unique}-tracker"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique)},
            manufacturer=MANUFACTURER,
            name=device_name,
        )

    @property
    def latitude(self):
        return self.coordinator.data.get("lat")

    @property
    def longitude(self):
        return self.coordinator.data.get("lon")

    @property
    def location_accuracy(self):
        return self.coordinator.data.get("accuracy")
