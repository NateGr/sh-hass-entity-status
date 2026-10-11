"""Services for SmartHass Entity Status integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse

from .const import DOMAIN
from .coordinator import SHEntityStatusCoordinator


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services."""

    async def _refresh_registry(call: ServiceCall) -> None:
        """Refresh the internal registry hierarchy."""
        for coordinator in hass.data.get(DOMAIN, {}).values():
            if isinstance(coordinator, SHEntityStatusCoordinator):
                await coordinator.async_refresh_registry()

    async def _poll_unavailable(call: ServiceCall) -> None:
        """Immediately poll for unavailable entities."""
        for coordinator in hass.data.get(DOMAIN, {}).values():
            if isinstance(coordinator, SHEntityStatusCoordinator):
                await coordinator.async_request_refresh()

    async def _reload(call: ServiceCall) -> None:
        """Reload all config entries for this integration."""
        for entry in hass.config_entries.async_entries(DOMAIN):
            await hass.config_entries.async_reload(entry.entry_id)

    async def _get_registry(call: ServiceCall) -> dict[str, Any]:
        """Return every loaded entry's complete mapped hierarchy, not sensor data."""
        return {
            "schema_version": 1,
            "entries": {
                entry_id: coordinator.async_get_registry()
                for entry_id, coordinator in hass.data.get(DOMAIN, {}).items()
                if isinstance(coordinator, SHEntityStatusCoordinator)
            },
        }

    hass.services.async_register(DOMAIN, "refresh_registry", _refresh_registry)
    hass.services.async_register(DOMAIN, "poll_unavailable", _poll_unavailable)
    hass.services.async_register(DOMAIN, "reload", _reload)
    hass.services.async_register(
        DOMAIN,
        "get_registry",
        _get_registry,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove integration services."""
    hass.services.async_remove(DOMAIN, "refresh_registry")
    hass.services.async_remove(DOMAIN, "poll_unavailable")
    hass.services.async_remove(DOMAIN, "reload")
    hass.services.async_remove(DOMAIN, "get_registry")
