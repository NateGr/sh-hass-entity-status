"""SmartHass Entity Status custom integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, ENTITY_ID_PREFIX
from .coordinator import SHEntityStatusCoordinator
from .services import async_setup_services, async_unload_services

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


def _migrate_entity_registry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rename list entities and remove the retired count entities."""
    entity_registry = er.async_get(hass)
    for old_key, new_key in (
        ("unsuppressed_unavailable_list", "unsuppressed_list"),
        ("suppressed_unavailable_list", "suppressed_list"),
    ):
        old_unique_id = f"{entry.entry_id}_{DOMAIN}_{old_key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, old_unique_id)
        if entity_id is None:
            continue

        new_unique_id = f"{entry.entry_id}_{DOMAIN}_{new_key}"
        new_entity_id = (
            f"sensor.{ENTITY_ID_PREFIX}_{new_key}"
            if ENTITY_ID_PREFIX
            else f"sensor.{new_key}"
        )
        entity_registry.async_update_entity(
            entity_id,
            new_entity_id=new_entity_id,
            new_unique_id=new_unique_id,
        )

    for old_key in (
        "unsuppressed_unavailable_count",
        "suppressed_unavailable_count",
    ):
        unique_id = f"{entry.entry_id}_{DOMAIN}_{old_key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id is not None:
            entity_registry.async_remove(entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartHass Entity Status from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    _migrate_entity_registry(hass, entry)

    coordinator = SHEntityStatusCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services only once (guard against multiple entries)
    if not hass.services.has_service(DOMAIN, "refresh_registry"):
        await async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: SHEntityStatusCoordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_teardown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove services when no more entries remain
    if not hass.data[DOMAIN]:
        await async_unload_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
