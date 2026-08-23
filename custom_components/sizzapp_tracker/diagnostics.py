from __future__ import annotations
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.diagnostics import async_redact_data

from .const import DOMAIN, CONF_SHARED_CODE, CONF_SHARE_URL

# Der Shared-Code ist das einzige Geheimnis, das den Standort-Feed schützt.
# Er steckt sowohl im Feld shared_code als auch in der share_url – beide
# müssen aus dem Diagnose-Download entfernt werden.
TO_REDACT = {CONF_SHARED_CODE, CONF_SHARE_URL}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coord = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "last_data": getattr(coord, "data", None),
    }
