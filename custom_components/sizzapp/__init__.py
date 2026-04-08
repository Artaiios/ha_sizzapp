from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS, CONF_SHARED_CODE, CONF_SHARE_URL, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
from .coordinator import SizzappCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    shared_code: str = entry.data.get(CONF_SHARED_CODE, "")
    share_url: str | None = entry.data.get(CONF_SHARE_URL)
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    coordinator = SizzappCoordinator(hass, shared_code, share_url, poll_interval)
    await coordinator.async_config_entry_first_refresh()

    if coordinator.last_update_success is False:
        raise ConfigEntryNotReady("Initial update failed")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Options-Änderungen sofort übernehmen (kein Neustart nötig)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload bei Options-Änderung."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
