DOMAIN = "sizzapp"
MANUFACTURER = "Sizzapp"

# Passe diese URL ggf. an dein echtes Share-API-Endpunktformat an:
API_URL = "https://api.sizzapp.com/app/location_sharing/info?shared_code={code}"

CONF_SHARED_CODE = "shared_code"
CONF_SHARE_URL = "share_url"
CONF_POLL_INTERVAL = "poll_interval"
CONF_SPEED_UNIT = "speed_unit"       # "kmh" | "mph"
CONF_COORD_PRECISION = "coord_precision"  # int (0..6)

DEFAULT_POLL_INTERVAL = 60  # Sekunden
DEFAULT_SPEED_UNIT = "kmh"
DEFAULT_COORD_PRECISION = 6

PLATFORMS = ["device_tracker", "sensor"]
