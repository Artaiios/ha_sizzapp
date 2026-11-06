from __future__ import annotations

import hashlib
import inspect
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

# HA 2026.11+: Geräte gehören genau einem Config-Entry und werden mit
# new_config_entry_id verschoben; add_config_entry_id ist deprecated (Ende
# 2027.8). Ältere Versionen (ab 2026.3, siehe hacs.json) kennen nur add_….
_DEVICE_MOVE_SUPPORTED = "new_config_entry_id" in inspect.signature(
    dr.DeviceRegistry.async_update_device
).parameters


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

    # Reihenfolge ist wichtig: ERST Entitäten, DANN Geräte. Verschiebt man ein
    # Gerät auf den neuen Config-Entry, entfernt Home Assistant alle Entitäten
    # dieses Geräts, die noch am alten Entry hängen (Verlust von Verlauf und
    # entity_id). Hängen die Entitäten schon am neuen Entry, bleiben sie erhalten.

    # --- Entitäten ---
    # Instanz-Isolation über legacy_prefix (enthält den Code dieser Instanz).
    # Die device_ids der übernommenen Entitäten bestimmen anschließend, welche
    # Geräte umziehen – auch Geräte gerade offline gemeldeter Units.
    legacy_device_ids: set[str] = set()
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

        try:
            # Gerät bleibt dasselbe (device_id ändert sich beim Verschieben nicht).
            ent_reg.async_update_entity_platform(
                reg_entry.entity_id,
                DOMAIN,
                new_unique_id=new_unique_id,
                new_config_entry_id=entry.entry_id,
            )
            if reg_entry.device_id:
                legacy_device_ids.add(reg_entry.device_id)
            # NUR entity_id loggen – unique_ids enthalten das Geheimnis nicht mehr,
            # aber die entity_id ist ohnehin der unbedenklichste Bezeichner.
            _LOGGER.info("Migrated Sizzapp entity %s to new domain '%s'", reg_entry.entity_id, DOMAIN)
        except Exception:  # noqa: BLE001 – Migration darf den Setup nie blockieren
            # Typischer Grund: der alte 'sizzapp'-Eintrag ist noch geladen
            # ("Only entities that haven't been loaded can be migrated").
            _LOGGER.exception(
                "Could not migrate Sizzapp entity %s – disable the old 'sizzapp' "
                "entry first, then reload this entry",
                reg_entry.entity_id,
            )

    # --- Geräte ---
    # Über die device_ids der übernommenen Entitäten statt die gesamte
    # Device-Registry zu durchlaufen (dev_reg.devices als Mapping ist seit
    # HA 2026.11 deprecated).
    for device_id in legacy_device_ids:
        device = dev_reg.async_get(device_id)
        if device is None:
            continue
        if not any(dom == LEGACY_DOMAIN for (dom, _uid) in device.identifiers):
            continue

        new_identifiers = {
            (DOMAIN, unit_id) if dom == LEGACY_DOMAIN else (dom, unit_id)
            for (dom, unit_id) in device.identifiers
        }
        update_kwargs: dict = {"new_identifiers": new_identifiers}
        if _DEVICE_MOVE_SUPPORTED:
            # Ab HA 2026.11 gehört ein Gerät genau einem Config-Entry; ein nur per
            # add_config_entry_id "hinzugefügter" Entry wird ignoriert – das Gerät
            # bliebe am alten Entry und HA legte ein Duplikat an (Bereich usw.
            # gingen verloren). Daher das Gerät verschieben.
            update_kwargs["new_config_entry_id"] = entry.entry_id
        else:
            update_kwargs["add_config_entry_id"] = entry.entry_id
        if device.disabled_by is dr.DeviceEntryDisabler.CONFIG_ENTRY:
            # Der alte Entry ist (laut Anleitung) deaktiviert; das Gerät soll am
            # neuen, aktiven Entry wieder aktiv sein.
            update_kwargs["disabled_by"] = None
        try:
            dev_reg.async_update_device(device.id, **update_kwargs)
            _LOGGER.info("Migrated Sizzapp device %s to new domain '%s'", device.id, DOMAIN)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Could not migrate Sizzapp device %s", device.id)


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
