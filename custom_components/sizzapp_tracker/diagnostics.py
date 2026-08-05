from __future__ import annotations
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_SHARE_URL


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    data = dict(entry.data)
    if CONF_SHARE_URL in data:
        url = data[CONF_SHARE_URL]
        data[CONF_SHARE_URL] = f"{url[:32]}…"
    coord = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    return {"entry": data, "last_data": getattr(coord, "data", None)}
