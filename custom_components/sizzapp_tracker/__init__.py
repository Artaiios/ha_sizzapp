from __future__ import annotations

import hashlib
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


def _entry_unique_id(uid_source: str) -> str:
    """Nicht-umkehrbare Entry-unique_id aus Code/URL (muss config_flow spiegeln)."""
    digest = hashlib.sha256((uid_source or "").encode("utf-8")).hexdigest()
    return f"sizzapp_tracker::{digest}"


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config-Entry-Migration.

    v1.3.4 (minor_version 2): Die Entry-unique_id war bis dahin der rohe
    Share-Code (bzw. die Share-URL) und wurde damit im Klartext nach
    .storage/core.config_entries persistiert. Wir ersetzen sie durch einen
    sha256-Hash. Idempotent und versions-gegatet.
    """
    if entry.version == 1 and entry.minor_version < 2:
        uid_source = entry.data.get(CONF_SHARED_CODE, "") or entry.data.get(CONF_SHARE_URL, "") or ""
        new_uid = _entry_unique_id(uid_source)

        if entry.unique_id == new_uid:
            hass.config_entries.async_update_entry(entry, minor_version=2)
        else:
            existing = hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, new_uid)
            if existing is None or existing.entry_id == entry.entry_id:
                hass.config_entries.async_update_entry(entry, unique_id=new_uid, minor_version=2)
            else:
                # Ziel-uid schon von einem anderen Entry belegt (zwei Entries mit
                # gleichem Code). Trotzdem den Klartext-Code aus der uid entfernen
                # – mit entry_id gesalzen, damit die uid kollisionsfrei bleibt.
                salted = _entry_unique_id(f"{uid_source}#{entry.entry_id}")
                hass.config_entries.async_update_entry(entry, unique_id=salted, minor_version=2)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    shared_code: str = entry.data.get(CONF_SHARED_CODE, "")
    share_url: str | None = entry.data.get(CONF_SHARE_URL)
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    coordinator = SizzappCoordinator(hass, shared_code, share_url, poll_interval)
    await coordinator.async_config_entry_first_refresh()

    if coordinator.last_update_success is False:
        raise ConfigEntryNotReady("Initial update failed")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Bestehende Nutzer übernehmen, BEVOR die Plattformen ihre Entitäten anlegen
    # (sonst entstehen Duplikate). Deckt zwei Übergänge ab:
    #   A) uralte Domain "sizzapp" -> "sizzapp_tracker" (+ Token statt Code)
    #   B) v1.3.0–v1.3.3: Klartext-Code im unique_id -> Token
    _async_migrate_registry(hass, entry, coordinator.code_hint, coordinator.code_token)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Options-Änderungen sofort übernehmen (kein Neustart nötig)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


def _async_migrate_registry(
    hass: HomeAssistant, entry: ConfigEntry, code_hint: str, code_token: str
) -> None:
    """Registry-Migration der Geräte/Entitäten dieser Instanz.

    Der Share-Code (code_hint) ist ein Geheimnis und darf nicht in
    persistierten unique_ids stehen. Ab v1.3.4 verwenden unique_ids den
    nicht-umkehrbaren code_token (sha256-Präfix). Bestandsnutzer werden hier
    einmalig übernommen, ohne Verlust von Verlauf/Anpassungen/Automationen.

    Idempotent: bereits migrierte Einträge (Token bereits im unique_id) werden
    nicht erneut angefasst.
    """
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    token_prefix = f"{DOMAIN}_{code_token}_"        # Ziel- / Fall-C-Präfix
    _migrate_legacy_domain(hass, entry, code_hint, token_prefix, ent_reg, dev_reg)
    _migrate_plaintext_uid(hass, entry, code_hint, token_prefix, ent_reg)


def _migrate_legacy_domain(
    hass: HomeAssistant,
    entry: ConfigEntry,
    code_hint: str,
    token_prefix: str,
    ent_reg,
    dev_reg,
) -> None:
    """Fall A: uralte Domain 'sizzapp' -> 'sizzapp_tracker' (+ Token statt Code).

    Geräte-Identifier (sizzapp, unit) -> (sizzapp_tracker, unit) und Entitäten
    per async_update_entity_platform (Plattformwechsel) direkt auf die
    Token-unique_id umschreiben (keine Klartext-Zwischenstufe).
    """
    legacy_prefix = f"{LEGACY_DOMAIN}_{code_hint}_"  # "sizzapp_<code>_"

    # Instanz-Isolation für Geräte über die unit_ids der Legacy-ENTITÄTEN dieser
    # Instanz (deren unique_id mit legacy_prefix beginnt) – NICHT über die aktuell
    # online Units. Sonst blieben Geräte offline-Units unmigriert, während ihre
    # Entitäten schon umziehen (verwaiste/doppelte Geräte).
    instance_unit_ids: set[str] = set()
    for reg_entry in list(ent_reg.entities.values()):
        if reg_entry.platform == LEGACY_DOMAIN and reg_entry.unique_id.startswith(legacy_prefix):
            rest = reg_entry.unique_id[len(legacy_prefix):]
            uid = rest.split("_", 1)[0] if rest else None
            if uid:
                instance_unit_ids.add(uid)

    # --- Geräte ---
    unit_to_device: dict[str, str] = {}
    for device in list(dev_reg.devices.values()):
        legacy_ids = {i for i in device.identifiers if i[0] == LEGACY_DOMAIN}
        if not legacy_ids:
            continue
        # Nur Geräte, deren unit_id zu einer Legacy-Entität dieser Instanz gehört
        # (online ODER offline) – so bleiben Gerät und Entität konsistent.
        if not any(unit_id in instance_unit_ids for (_dom, unit_id) in legacy_ids):
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
            _LOGGER.info("Migrated Sizzapp device %s to new domain '%s'", device.id, DOMAIN)
        except Exception:  # noqa: BLE001 – Migration darf den Setup nie blockieren
            _LOGGER.exception("Could not migrate Sizzapp device %s", device.id)

    # --- Entitäten ---
    for reg_entry in list(ent_reg.entities.values()):
        if reg_entry.platform != LEGACY_DOMAIN:
            continue
        if not reg_entry.unique_id.startswith(legacy_prefix):
            continue

        # "<unit_id>_<key>" hinter dem Legacy-Präfix; Ziel direkt mit Token.
        rest = reg_entry.unique_id[len(legacy_prefix):]
        new_unique_id = token_prefix + rest

        if ent_reg.async_get_entity_id(reg_entry.domain, DOMAIN, new_unique_id):
            continue  # Ziel existiert bereits -> alte Zeile in Ruhe lassen

        unit_id = rest.split("_", 1)[0] if rest else None
        new_device_id = unit_to_device.get(unit_id)
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
            # NUR entity_id loggen – unique_ids enthalten das Geheimnis nicht mehr,
            # aber die entity_id ist ohnehin der unbedenklichste Bezeichner.
            _LOGGER.info("Migrated Sizzapp entity %s to new domain '%s'", reg_entry.entity_id, DOMAIN)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Could not migrate Sizzapp entity %s", reg_entry.entity_id)


def _migrate_plaintext_uid(
    hass: HomeAssistant,
    entry: ConfigEntry,
    code_hint: str,
    token_prefix: str,
    ent_reg,
) -> None:
    """Fall B: v1.3.0–v1.3.3 – Klartext-Code im unique_id -> Token.

    Gleiche Domain und gleiches Gerät; nur die unique_id wird umgeschrieben
    (async_update_entity, kein Plattform-/Device-Wechsel nötig).
    """
    plain_prefix = f"{DOMAIN}_{code_hint}_"  # "sizzapp_tracker_<code>_"

    # Fall C (bereits Token) fällt hier automatisch raus: token_prefix != plain_prefix
    # außer im pathologischen Fixpunkt (code == sha256(code)[:16]) – dann ist
    # ohnehin nichts zu tun.
    if plain_prefix == token_prefix:
        return

    for reg_entry in list(ent_reg.entities.values()):
        if reg_entry.platform != DOMAIN:
            continue
        if reg_entry.config_entry_id != entry.entry_id:
            continue  # Instanz-Isolation
        if not reg_entry.unique_id.startswith(plain_prefix):
            continue

        new_unique_id = token_prefix + reg_entry.unique_id[len(plain_prefix):]

        if ent_reg.async_get_entity_id(reg_entry.domain, DOMAIN, new_unique_id):
            continue  # Ziel existiert bereits

        try:
            ent_reg.async_update_entity(reg_entry.entity_id, new_unique_id=new_unique_id)
            _LOGGER.info("Rekeyed Sizzapp entity %s to hashed unique_id", reg_entry.entity_id)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Could not rekey Sizzapp entity %s", reg_entry.entity_id)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload bei Options-Änderung."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
