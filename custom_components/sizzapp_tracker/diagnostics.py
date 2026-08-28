from __future__ import annotations
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.diagnostics import async_redact_data

from .const import DOMAIN, CONF_SHARED_CODE, CONF_SHARE_URL

# Der Shared-Code ist das einzige Geheimnis, das den Standort-Feed schützt.
# Er steckt im Feld shared_code und in der share_url; zusätzlich könnte die API
# den Code theoretisch in per-Unit-Feldern zurückspiegeln – defensiv mit-redigieren.
TO_REDACT = {
    CONF_SHARED_CODE,
    CONF_SHARE_URL,
    "share_link",
    "url",
    "link",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coord = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    # last_data ist die rohe API-Antwort je Unit – ebenfalls durch die Redaktion
    # schicken, falls die API den Code in einem Feld zurückspiegelt.
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "last_data": async_redact_data(getattr(coord, "data", None) or {}, TO_REDACT),
    }
