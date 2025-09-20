# Sizzapp Location Sharing (Home Assistant)

Custom-Integration, which does the "sharing API" `https://api.sizzapp.com/app/location_sharing/info?shared_code=<CODE>` request includes as a sensor in HA

## Installation (HACS)
1. HACS → Integrations → ⋯ → *Custom repositories* → `https://github.com/Artaiios/ha_sizzapp` (Category: *Integration*).
2. Install Integration, Restart Home Assistant
3. Settings → Devices & Services → *add Integration → **Sizzapp Location Sharing**.
4. Within the Sizzapp Application on your phone, create a new "tracking" link our copy an excisting one
5. Copy & Paste the full URL or Tracking Code/Sharing Code (last part of the URL after "/") into the integration config.
6. Done!
7. You can customize the pull interval (default 60sec) and the speed units (kmh or miles)
8. Multiple Hubs for Multiple Tracker can be created (tested on up to three SIZZAPP Tracker)
