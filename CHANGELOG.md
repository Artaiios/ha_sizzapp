# Changelog

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
