"""Config flow for SmartHass Entity Status integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_IGNORE_LABEL,
    CONF_POLL_INTERVAL,
    CONF_REFRESH_INTERVAL,
    DEFAULT_IGNORE_LABEL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    INTEGRATION_NAME,
)


def _build_schema(defaults: dict) -> vol.Schema:
    # TODO: Replace ignore_label text field with a dynamic label picker
    # once HA's label registry exposes a convenient selector in config flows.
    return vol.Schema(
        {
            vol.Required("title", default=defaults.get("title", INTEGRATION_NAME)): str,
            vol.Required(
                CONF_IGNORE_LABEL,
                default=defaults.get(CONF_IGNORE_LABEL, DEFAULT_IGNORE_LABEL),
            ): str,
            vol.Required(
                CONF_REFRESH_INTERVAL,
                default=defaults.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(
                CONF_POLL_INTERVAL,
                default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
        }
    )


class SHEntityStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow for SmartHass Entity Status."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the user step."""
        # Enforce a single config entry — prevents entity_id/unique_id collisions.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            title = user_input.pop("title", INTEGRATION_NAME)
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema({}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SHEntityStatusOptionsFlow:
        """Return the options flow handler."""
        return SHEntityStatusOptionsFlow()


class SHEntityStatusOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SmartHass Entity Status."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the options step."""
        current = {
            "title": self.config_entry.title,
            **self.config_entry.data,
            **self.config_entry.options,
        }

        if user_input is not None:
            # TODO: Replace ignore_label text field with dynamic label picker
            # once HA's label registry exposes a convenient selector in options flows.
            title = user_input.pop("title", self.config_entry.title)
            # Persist the new title so users can rename the integration via the options flow.
            self.hass.config_entries.async_update_entry(self.config_entry, title=title)
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(current),
        )
