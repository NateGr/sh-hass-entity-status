"""Config flow for SH Entity Status integration."""
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
)


def _build_schema(defaults: dict) -> vol.Schema:
    # TODO: Replace ignore_label text field with a dynamic label picker
    # once HA's label registry exposes a convenient selector in config flows.
    return vol.Schema(
        {
            vol.Required("title", default=defaults.get("title", "SH Entity Status")): str,
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
    """Handle the initial config flow for SH Entity Status."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the user step."""
        if user_input is not None:
            title = user_input.pop("title", "SH Entity Status")
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema({}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "SHEntityStatusOptionsFlow":
        """Return the options flow handler."""
        return SHEntityStatusOptionsFlow(config_entry)


class SHEntityStatusOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SH Entity Status."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the options step."""
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            # TODO: Replace ignore_label text field with dynamic label picker
            user_input.pop("title", None)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(current),
        )
