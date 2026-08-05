from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    DOMAIN,
    LEGACY_DOMAIN,
    PLATFORMS,
    CONF_SHARED_CODE,
    CONF_SHARE_URL,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
)
from .coordinator import SizzappCoordinator

_LOGGER = logging.getLogger(__name__)

# Präfixe der Entity-unique_ids vor/ab v1.3.0.
_LEGACY_UID_PREFIX = f"{LEGACY_DOMAIN}_"      # "sizzapp_"
_NEW_UID_PREFIX = f"{DOMAIN}_"                # "sizzapp_tracker_"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    shared_code: str = entry.data.get(CONF_SHARED_CODE, "")
    share_url: str | None = entry.data.get(CONF_SHARE_URL)
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    coordinator = SizzappCoordinator(hass, shared_code, share_url, poll_interval)
    await coordinator.async_config_entry_first_refresh()

    if coordinator.last_update_success is False:
        raise ConfigEntryNotReady("Initial update failed")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Bestehende Nutzer der alten Domain "sizzapp" übernehmen: verwaiste Geräte-
    # und Entitäts-Registry-Einträge auf die neue Domain umhängen, BEVOR die
    # Plattformen ihre Entitäten anlegen (sonst entstehen Duplikate).
    _async_migrate_legacy_registrations(hass, entry, coordinator.code_hint)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Options-Änderungen sofort übernehmen (kein Neustart nötig)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


def _async_migrate_legacy_registrations(
    hass: HomeAssistant, entry: ConfigEntry, code_hint: str
) -> None:
    """Einmalige Migration von der alten Domain 'sizzapp' auf 'sizzapp_tracker'.

    Home Assistant kann einen Config-Entry nicht über die Domain hinweg
    verschieben. Wenn ein Nutzer die Integration unter der neuen Domain neu
    hinzufügt, hängen wir hier seine bisherigen Geräte und Entitäten (aus der
    alten Domain) an den neuen Entry um und schreiben die unique_ids/Identifier
    um – so bleiben Verlauf, Anpassungen und Automationen erhalten.

    Idempotent: bereits migrierte Einträge werden übersprungen.
    """
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    # unit_ids dieser Instanz (aus den aktuellen Coordinator-Daten). Nur diese
    # Geräte/Entitäten gehören uns – wichtig, wenn mehrere Instanzen existieren.
    known_unit_ids = {str(uid) for uid in (hass.data[DOMAIN][entry.entry_id].data or {})}
    # Nur die unique_ids dieser Instanz beginnen mit "sizzapp_<code_hint>_".
    instance_uid_prefix = f"{_LEGACY_UID_PREFIX}{code_hint}_"

    # --- Geräte: identifiers (LEGACY_DOMAIN, unit_id) -> (DOMAIN, unit_id) ---
    # Map unit_id -> (neue) device_id, um Entitäten anschließend korrekt anzuhängen.
    unit_to_device: dict[str, str] = {}
    for device in list(dev_reg.devices.values()):
        legacy_ids = {i for i in device.identifiers if i[0] == LEGACY_DOMAIN}
        if not legacy_ids:
            continue
        # Nur Geräte dieser Instanz (unit_id muss zu den aktuellen Daten passen).
        if not any(unit_id in known_unit_ids for (_dom, unit_id) in legacy_ids):
            continue

        new_identifiers = {
            (DOMAIN, unit_id) if dom == LEGACY_DOMAIN else (dom, unit_id)
            for (dom, unit_id) in device.identifiers
        }
        try:
            dev_reg.async_update_device(
                device.id,
                new_identifiers=new_identifiers,
                add_config_entry_id=entry.entry_id,
            )
            for _dom, unit_id in legacy_ids:
                unit_to_device[unit_id] = device.id
            _LOGGER.info(
                "Migrated Sizzapp device %s to new domain '%s'", device.id, DOMAIN
            )
        except Exception:  # noqa: BLE001 – Migration darf den Setup nie blockieren
            _LOGGER.exception("Could not migrate Sizzapp device %s", device.id)

    # --- Entitäten: platform 'sizzapp' + unique_id-Präfix -> neu umschreiben ---
    for reg_entry in list(ent_reg.entities.values()):
        if reg_entry.platform != LEGACY_DOMAIN:
            continue
        if not reg_entry.unique_id.startswith(instance_uid_prefix):
            continue

        new_unique_id = _NEW_UID_PREFIX + reg_entry.unique_id[len(_LEGACY_UID_PREFIX):]
        # Kollisionsschutz: existiert das Ziel bereits, alte Zeile in Ruhe lassen.
        if ent_reg.async_get_entity_id(reg_entry.domain, DOMAIN, new_unique_id):
            continue

        # unit_id aus "sizzapp_<code_hint>_<unit_id>_<key>" extrahieren, um die
        # Entität an das passende (bereits migrierte) Gerät zu hängen.
        rest = reg_entry.unique_id[len(instance_uid_prefix):]
        unit_id = rest.split("_", 1)[0] if rest else None
        new_device_id = unit_to_device.get(unit_id)

        # new_device_id nur setzen, wenn wir wirklich ein Gerät haben – None würde
        # die Entität sonst von ihrem Gerät lösen (statt es unverändert zu lassen).
        extra: dict[str, str] = {}
        if new_device_id is not None:
            extra["new_device_id"] = new_device_id

        try:
            ent_reg.async_update_entity_platform(
                reg_entry.entity_id,
                DOMAIN,
                new_unique_id=new_unique_id,
                new_config_entry_id=entry.entry_id,
                **extra,
            )
            _LOGGER.info(
                "Migrated Sizzapp entity %s (%s -> %s)",
                reg_entry.entity_id,
                reg_entry.unique_id,
                new_unique_id,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Could not migrate Sizzapp entity %s", reg_entry.entity_id
            )


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload bei Options-Änderung."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
