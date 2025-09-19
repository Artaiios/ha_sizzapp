from __future__ import annotations
from datetime import timedelta
from typing import Any, Dict, List
import asyncio
from yarl import URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, API_URL, API_PARAM, CONF_SHARED_CODE, CONF_SHARE_URL, CONF_POLL_INTERVAL


class SizzappCoordinator(DataUpdateCoordinator[Dict[int, Dict[str, Any]]]):
    """Koordinator pollt die Share-API und liefert Einheiten nach unit_id indiziert."""

    def __init__(self, hass: HomeAssistant, shared_code: str, share_url: str | None, poll_interval: int) -> None:
        self.hass = hass
        self._shared_code = shared_code
        self._share_url = share_url
        self.session = async_get_clientsession(hass)
        super().__init__(
            hass,
            hass.helpers.logger.logging.getLogger(f"{DOMAIN}.coordinator"),
            name=f"{DOMAIN}-{shared_code}",
            update_interval=timedelta(seconds=poll_interval),
        )

    @property
    def api_url(self) -> str:
        if self._share_url:
            return self._share_url
        return str(URL(API_URL).with_query({API_PARAM: self._shared_code}))

    async def _async_update_data(self) -> Dict[int, Dict[str, Any]]:
        try:
            async with self.session.get(self.api_url, timeout=10) as resp:
                status = resp.status
                if status == 404:
                    raise UpdateFailed("not_found")
                if status in (401, 403):
                    raise UpdateFailed("invalid_code")
                if status == 429:
                    raise UpdateFailed("rate_limited")
                resp.raise_for_status()
                payload = await resp.json()

        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"timeout: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(err) from err

        if not isinstance(payload, dict) or "data" not in payload:
            raise UpdateFailed("unexpected_response")

        units: List[Dict[str, Any]] = payload.get("data") or []
        mapped: Dict[int, Dict[str, Any]] = {}
        for u in units:
            uid = u.get("unit_id")
            if uid is None:
                continue
            mapped[int(uid)] = u
        return mapped
