from __future__ import annotations

from datetime import timedelta
import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_SHARED_CODE, DEFAULT_SCAN_INTERVAL, API_URL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]


class SizzappCoordinator(DataUpdateCoordinator[dict[str, Any] | None]):
    def __init__(self, hass: HomeAssistant, shared_code: str, interval_seconds: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Sizzapp ({shared_code[:6]}…)",
            update_interval=timedelta(seconds=interval_seconds),
        )
        self._shared_code = shared_code

    async def _async_update_data(self) -> dict[str, Any] | None:
        url = API_URL.format(code=self._shared_code)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"HTTP {resp.status}")
                    data = await resp.json(content_type=None)
        except asyncio.TimeoutError as e:
            raise UpdateFailed("Timeout while contacting Sizzapp") from e
        except Exception as e:  # noqa: BLE001
            raise UpdateFailed(f"Error fetching Sizzapp data: {e}") from e

        # Expect {"success": true, "data": [ {...} ]}
        if not isinstance(data, dict) or not data.get("success"):
            raise UpdateFailed("Unexpected API response (success != true)")

        items = data.get("data") or []
        if not items:
            # Valid, aber keine Daten – gib None zurück; Entity bleibt, state wird unverändert
            _LOGGER.debug("Sizzapp returned empty data list")
            return None

        first = items[0]
        if not isinstance(first, dict):
            raise UpdateFailed("Unexpected data format")

        # Normiere Schlüssel, falls nötig, und gib das Objekt durch
        return first


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    shared_code: str = entry.data[CONF_SHARED_CODE]
    interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = SizzappCoordinator(hass, shared_code, interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Options-Listener: bei Änderung Neu-Laden
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def _options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
