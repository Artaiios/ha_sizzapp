from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_SHARED_CODE, DEFAULT_SCAN_INTERVAL


class SizzappConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            shared_code = user_input[CONF_SHARED_CODE].strip()
            if not shared_code:
                errors["base"] = "invalid_shared_code"
            else:
                # unique_id = shared_code (ein Code = ein Eintrag)
                await self.async_set_unique_id(shared_code)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Sizzapp {shared_code[:6]}…", data={
                    CONF_SHARED_CODE: shared_code
                })

        schema = vol.Schema({
            vol.Required(CONF_SHARED_CODE): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(self, user_input=None) -> FlowResult:
        # Nicht genutzt (keine YAML-Importe)
        return await self.async_step_user(user_input)

    @staticmethod
    async def async_get_options_flow(config_entry):
        return SizzappOptionsFlowHandler(config_entry)


class SizzappOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(int, vol.Clamp(min=5, max=3600)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
