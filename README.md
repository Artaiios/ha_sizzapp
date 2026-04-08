# Sizzapp Location Sharing for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GitHub Release](https://img.shields.io/github/v/release/Artaiios/ha_sizzapp)](https://github.com/Artaiios/ha_sizzapp/releases)

Custom integration for [Home Assistant](https://www.home-assistant.io/) that pulls real-time location and status data from [Sizzapp](https://www.sizzapp.com/) GPS trackers via the sharing API.

No Sizzapp account credentials required — just a sharing link or code.

## What you get

Each configured tracker creates a device with the following entities:

| Entity | Type | Description |
|---|---|---|
| **Location** | `device_tracker` | GPS position on the HA map, with vehicle image from Sizzapp |
| **Speed** | `sensor` | Current speed (km/h or mph, configurable) |
| **Heading** | `sensor` | Direction of travel in degrees |
| **Last Update** | `sensor` | Timestamp of the last tracker report — useful for automations |
| **In Trip** | `binary_sensor` | Whether the vehicle is currently moving |
| **Stale** | `binary_sensor` | Turns on when the tracker hasn't reported in for a while (threshold configurable) |

## Installation

### Via HACS (recommended)

1. Open HACS → Integrations → three-dot menu → **Custom repositories**
2. Add `https://github.com/Artaiios/ha_sizzapp` with category **Integration**
3. Install the integration and restart Home Assistant
4. Go to Settings → Devices & Services → **Add Integration** → search for **Sizzapp Location Sharing**

### Manual

Copy the `custom_components/sizzapp` folder into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

1. In the Sizzapp app on your phone, create a tracking/sharing link (or copy an existing one)
2. Paste the full URL **or** just the sharing code into the integration setup — both work
3. Done!

### Options

After setup, you can configure:

- **Poll interval** — how often to fetch new data (default: 60s, minimum: 15s)
- **Speed unit** — km/h or mph
- **Coordinate precision** — decimal places for GPS coordinates (0–6, default: 6). Reducing this can be a simple privacy measure if you share your HA dashboard.
- **Stale threshold** — minutes without a tracker update before the Stale sensor turns on (default: 5)

All options take effect immediately, no restart needed.

## Multiple trackers

You can add multiple integration instances for different trackers — each creates its own device. Tested with up to three Sizzapp trackers simultaneously.

## Notes

- This integration uses the **public sharing API** only. It does not require your Sizzapp account credentials.
- The sharing API provides location, speed, heading, trip status, and the vehicle image. Battery voltage, eco-drive scores, and other advanced data from the Sizzapp app are not available through this API.
- The tracker image (if set in the Sizzapp app) shows up automatically as the entity picture.

## Links

- [Sizzapp Website](https://www.sizzapp.com/)
- [Changelog](CHANGELOG.md)
- [Issues / Feature Requests](https://github.com/Artaiios/ha_sizzapp/issues)
