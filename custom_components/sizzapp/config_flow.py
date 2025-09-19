from __future__ import annotations
from typing import Any
from urllib.parse import urlparse, parse_qs
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_SHARED_CODE,
    CONF_SHARE_URL,
    CONF_POLL_INTERVAL,
    CONF_SPEED_UNIT,
    CONF_COORD_PRECISION,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SPEED_UNIT,
    DEFAULT_COORD_PRECISION,
    API_URL,
    API_PARAM,
)


async def _validate(hass, share_url: str) -> dict[str, Any]:
    session = async_get_clientsession(hass)
    async with session.get(share_url, timeout=10) as resp:
        if resp.status == 404:
            raise ValueError("not_found")
        if resp.status in (401, 403):
            raise ValueError("invalid_code")
        if resp.status == 429:
            raise ValueError("rate_limited")
        resp.raise_for_status()
        data = await resp.json()
    if not isinstance(data, dict) or "data" not in data:
        raise ValueError("unexpected_response")
    return data


def _normalize_inputs(shared_code_raw: str, share_url_raw: str) -> tuple[str, str]:
    shared_code = (shared_code_raw or "").strip()
    share_url = (share_url_raw or "").strip()

    def _try_extract_code_from_url(val: str) -> str | None:
        try:
            p = urlparse(val)
            if p.scheme and p.netloc:
                qs = parse_qs(p.query)
                code = qs.get(API_PARAM, [None])[0]
                return code
        except Exception:
            pass
        return None

    if not share_url:
        maybe_code = _try_extract_code_from_url(shared_code)
        if maybe_code:
            shared_code = maybe_code
            share_url = f"{API_URL}?{API_PARAM}={shared_code}"
        elif shared_code:
            share_url = f"{API_URL}?{API_PARAM}={shared_code}"
    else:
        code_from_url = _try_extract_code_from_url(share_url)
        if code_from_url:
            shared_code = shared_code or code_from_url

    return shared_code, share_url


class SizzappConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            shared_code, share_url = _normalize_inputs(
                user_input.get(CONF_SHARED_CODE), user_input.get(CONF_SHARE_URL)
            )

            try:
                p = urlparse(share_url)
                if not p.scheme or not p.netloc:
                    raise ValueError("bad_url")
            except Exception:
                errors["base"] = "bad_url"
            else:
                try:
                    await _validate(self.hass, share_url)
                except ValueError as e:
                    errors["base"] = str(e)
                except Exception:
                    errors["base"] = "cannot_connect"

            if not errors:
                uid = shared_code or share_url
                await self.async_set_unique_id(f"sizzapp::{uid}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Sizzapp",
                    data={CONF_SHARED_CODE: shared_code, CONF_SHARE_URL: share_url},
                )

        data_schema = {
            CONF_SHARED_CODE: str,
            CONF_SHARE_URL: str,
        }
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SizzappOptionsFlow(config_entry)


class SizzappOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                poll = int(user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
                if poll < 15:
                    errors["base"] = "poll_too_low"
                else:
                    return self.async_create_entry(title="", data=user_input)
            except Exception:
                errors["base"] = "unknown"

        data_schema = {
            CONF_POLL_INTERVAL: int,
            CONF_SPEED_UNIT: str,
            CONF_COORD_PRECISION: int,
        }
        defaults = {
            CONF_POLL_INTERVAL: self._entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            CONF_SPEED_UNIT: self._entry.options.get(CONF_SPEED_UNIT, DEFAULT_SPEED_UNIT),
            CONF_COORD_PRECISION: self._entry.options.get(CONF_COORD_PRECISION, DEFAULT_COORD_PRECISION),
        }
        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors, description_placeholders=defaults)
