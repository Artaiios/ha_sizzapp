from __future__ import annotations
from typing import Any
from urllib.parse import urlparse, parse_qs

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from aiohttp import ClientError, ClientResponseError

from .const import (
    DOMAIN,
    CONF_SHARED_CODE,
    CONF_SHARE_URL,
    CONF_POLL_INTERVAL,
    CONF_SPEED_UNIT,
    CONF_COORD_PRECISION,
    CONF_STALE_MINUTES,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SPEED_UNIT,
    DEFAULT_COORD_PRECISION,
    DEFAULT_STALE_MINUTES,
    API_URL,
    API_PARAM,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SHARED_CODE): selector.TextSelector(),
        vol.Optional(CONF_SHARE_URL): selector.TextSelector(),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): selector.NumberSelector(
            selector.NumberSelectorConfig(min=15, max=3600, step=5, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_SPEED_UNIT, default=DEFAULT_SPEED_UNIT): selector.SelectSelector(
            selector.SelectSelectorConfig(options=["kmh", "mph"], mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Required(CONF_COORD_PRECISION, default=DEFAULT_COORD_PRECISION): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=6, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_STALE_MINUTES, default=DEFAULT_STALE_MINUTES): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=60, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
    }
)


async def _validate(hass, share_url: str) -> dict[str, Any]:
    """Test-Request an die API, um Eingaben zu validieren."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(share_url, timeout=10) as resp:
            status = resp.status
            if status == 404:
                raise ValueError("not_found")
            if status in (401, 403):
                raise ValueError("invalid_code")
            if status == 429:
                raise ValueError("rate_limited")
            resp.raise_for_status()
            data = await resp.json()
    except ClientResponseError as e:
        raise ValueError("cannot_connect") from e
    except (ClientError, TimeoutError) as e:
        raise ValueError("cannot_connect") from e
    except Exception as e:
        raise ValueError("unknown") from e

    if not isinstance(data, dict) or "data" not in data:
        raise ValueError("unexpected_response")
    return data


def _extract_code(val: str | None) -> str | None:
    """Extrahiert den Shared-Code aus reinem Code, Website-URL (/location/<code>) oder API-URL."""
    val = (val or "").strip()
    if not val:
        return None
    p = urlparse(val)
    if p.scheme and p.netloc:
        code = parse_qs(p.query).get(API_PARAM, [None])[0]  # API-URL: ?shared_code=...
        if code:
            return code.strip()
        segments = [s for s in p.path.split("/") if s]       # Website-URL: .../location/<code>
        return segments[-1].strip() if segments else None
    return val  # kein URL-Schema -> als reiner Code behandeln


def _normalize_inputs(shared_code_raw: str | None, share_url_raw: str | None) -> tuple[str, str]:
    """Nimmt Code ODER URL (beliebiges Feld) und liefert (code, api_url)."""
    raw = (share_url_raw or "").strip() or (shared_code_raw or "").strip()
    code = _extract_code(raw)
    if not code:
        return "", ""
    return code, f"{API_URL}?{API_PARAM}={code}"


class SizzappConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                shared_code, share_url = _normalize_inputs(
                    user_input.get(CONF_SHARED_CODE), user_input.get(CONF_SHARE_URL)
                )
                p = urlparse(share_url)
                if not (p.scheme and p.netloc):
                    raise ValueError("bad_url")

                await _validate(self.hass, share_url)

                uid = shared_code or share_url
                await self.async_set_unique_id(f"sizzapp_tracker::{uid}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Sizzapp",
                    data={CONF_SHARED_CODE: shared_code, CONF_SHARE_URL: share_url},
                )

            except ValueError as e:
                key = str(e) or "unknown"
                errors["base"] = key if key in {
                    "bad_url", "cannot_connect", "invalid_code", "not_found",
                    "rate_limited", "unexpected_response", "unknown"
                } else "unknown"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

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

        return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA, errors=errors)
