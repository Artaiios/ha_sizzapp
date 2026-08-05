# Changelog

## v1.3.0

**Domain-Umbenennung + Brand-Bilder (HACS-Review-Auflagen)**

- **Domain `sizzapp` → `sizzapp_tracker`.** Die bisherige Domain kollidierte mit der bereits im HACS-Katalog vorhandenen Integration `t4bias/ha-sizzapp`. Home Assistant unterscheidet Custom-Integrationen anhand der Domain, sodass beide nicht gleichzeitig installiert werden konnten. Der Komponenten-Ordner heißt jetzt `custom_components/sizzapp_tracker/`.
- **Automatische Migration für Bestandsnutzer.** Beim ersten Einrichten unter der neuen Domain werden vorhandene Geräte und Entitäten der alten Domain übernommen: Device-Identifier und Entity-`unique_id`s werden von `sizzapp…` auf `sizzapp_tracker…` umgeschrieben und an den neuen Config-Entry gehängt. Verlauf, Anpassungen und Automationen bleiben erhalten. (HA kann einen Config-Entry nicht über die Domain hinweg verschieben – daher muss die Integration einmalig neu hinzugefügt werden; siehe README.)
- **Brand-Bilder nach `custom_components/sizzapp_tracker/brand/` verschoben.** Seit Home Assistant 2026.3 wird ausschließlich dieser Pfad gelesen; die Icons lagen zuvor im Komponenten-Wurzelverzeichnis und wurden dadurch nicht mehr angezeigt.
- `code_hint`-Ableitung robuster gemacht (eigene Coordinator-Property statt Ableitung aus dem Coordinator-Namen), damit die Umbenennung die `unique_id`s nicht ungewollt verschiebt.

Keine funktionalen Änderungen an der Datenabfrage gegenüber v1.2.0.

## v1.2.0

**HACS-Default-Aufnahme**

- GitHub Actions hinzugefügt: HACS-Validierung (`hacs/action`) und `hassfest` laufen jetzt bei jedem Push/PR sowie täglich. Voraussetzung für die Aufnahme in den offiziellen HACS-Store.
- `manifest.json`: Schlüssel hassfest-konform sortiert (`domain`, `name`, dann alphabetisch).
- `hacs.json` bereinigt: ungültiger Wert `country: "all"` und der nur für Plugins relevante Schlüssel `filename` entfernt.

Keine funktionalen Änderungen gegenüber v1.1.2.

## v1.1.2

**Bugfix:** GPS-Koordinaten wurden nicht angezeigt (Device-Tracker-State "unknown"), weil `coord_precision` als Float aus den Options kam (`6.0`), Pythons `round()` aber einen Integer erwartet. Der daraus resultierende `TypeError` wurde still verschluckt und die Koordinaten als `None` zurückgegeben.

## v1.1.1

**Bugfix:** `entity_picture` wurde fälschlicherweise auf `DeviceInfo` gesetzt statt auf der Entity selbst – das hat den Platform-Setup abbrechen lassen und dazu geführt, dass keine Entitäten (inkl. Device-Tracker auf der Karte) geladen wurden. Das Bild wird jetzt korrekt nur auf dem Device-Tracker gesetzt.

## v1.1.0

**Neue Sensoren**

- **Last Update** (Timestamp-Sensor): Zeigt den Zeitpunkt des letzten Tracker-Updates als eigenen Sensor an – nicht mehr nur als verstecktes Attribut. Damit lassen sich jetzt Automationen bauen wie "wenn letztes Update älter als X Minuten".
- **Stale** (Binary-Sensor): Wird aktiv, wenn sich der Tracker länger als konfigurierbar viele Minuten nicht gemeldet hat. Gut geeignet als Offline-/Deep-Sleep-Indikator. Der Schwellwert ist über die Optionen einstellbar (Standard: 5 Minuten).

**Verbesserungen**

- Tracker-Bild aus der Sizzapp-API wird jetzt als `entity_picture` auf dem Device-Tracker angezeigt – das Fahrzeugbild erscheint direkt in der HA-Oberfläche.
- Koordinatenpräzision (`coord_precision`) wird jetzt tatsächlich auf die GPS-Koordinaten angewendet – vorher war die Option da, hat aber nichts gemacht.
- Options-Änderungen (Poll-Intervall, Speed-Unit, etc.) werden jetzt sofort übernommen, ohne dass HA neugestartet werden muss.
- Links in `manifest.json` zeigen jetzt auf das richtige Repository (`ha_sizzapp` statt `ha-sizzapp`).
- `strings.json` hinzugefügt (HA-Konvention für die Basis-Übersetzung).
- Unnötige `aiohttp`-Abhängigkeit aus `manifest.json` entfernt – ist ohnehin Teil von HA Core.

**Code-Qualität**

- Doppelt definierte `SizzappSpeedSensor`-Klasse in `sensor.py` bereinigt (toter Code aus der Entwicklungsphase).
- Gemeinsame `SizzappBaseEntity` in eigenes `entity.py` ausgelagert – war vorher in `sensor.py` und `binary_sensor.py` dupliziert.
- `async_reload_entry` aus `__init__.py` entfernt (wird durch den neuen `update_listener` abgedeckt).

## v1.0.1

Kleinere Bugfixes nach dem ersten Release.

## v1.0.0

Erstes Release. Unterstützt die Sizzapp Location Sharing API mit Device-Tracker, Speed-Sensor, Heading-Sensor und In-Trip Binary-Sensor. Konfiguration über den HA Config-Flow, anpassbares Poll-Intervall und Geschwindigkeitseinheit.
