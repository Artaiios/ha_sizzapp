from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, API_URL

class SizzappCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, shared_code: str):
        self.hass = hass
        self.shared_code = shared_code
        self.session = async_get_clientsession(hass)
        super().__init__(
            hass,
            logger=hass.helpers.logger.logging.getLogger(__package__),
            name=f"{DOMAIN}-{shared_code}",
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self):
        url = f"{API_URL}{self.shared_code}"
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 404:
                    raise UpdateFailed("not_found")
                if resp.status == 429:
                    raise UpdateFailed("rate_limited")
                resp.raise_for_status()
                return await resp.json()
        except Exception as err:
            raise UpdateFailed(err)
