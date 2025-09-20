# Sizzapp Location Sharing (Home Assistant)

Custom-Integration, die `https://api.sizzapp.com/app/location_sharing/info?shared_code=<CODE>` abfragt und als Sensor bereitstellt.

## Installation (HACS)
1. HACS → Integrations → ⋯ → *Custom repositories* → `https://github.com/Artaiios/ha_sizzapp` (Category: *Integration*).
2. Integration installieren, Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → *Integration hinzufügen* → **Sizzapp Location Sharing**.
4. Copy & Paste the full URL or Tracking Code/Sharing Code (last part of the URL after "/") into the config.
5. Done!
6. Multiple Hubs for Multiple Tracker can be created (tested up to three SIZZAPP Tracker)
