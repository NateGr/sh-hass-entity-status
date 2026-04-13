"""Button platform for SmartHass Entity Status integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ENTITY_ID_PREFIX, INTEGRATION_NAME
from .coordinator import SHEntityStatusCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartHass Entity Status buttons from a config entry."""
    coordinator: SHEntityStatusCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SHRefreshRegistryButton(coordinator, entry)])


class SHRefreshRegistryButton(ButtonEntity):
    """Button that triggers an immediate registry refresh."""

    def __init__(
        self,
        coordinator: SHEntityStatusCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        self._coordinator = coordinator
        self._attr_name = "Refresh Registry"
        self._attr_icon = "mdi:refresh"
        self._attr_unique_id = f"{entry.entry_id}_{DOMAIN}_refresh_registry"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=INTEGRATION_NAME,
            manufacturer="SmartHass",
            model="Entity Status Monitor",
        )
        self.entity_id = (
            f"button.{ENTITY_ID_PREFIX}_refresh_registry"
            if ENTITY_ID_PREFIX
            else "button.refresh_registry"
        )

    async def async_press(self) -> None:
        """Handle button press — rebuild registry and trigger a fresh poll."""
        await self._coordinator.async_refresh_registry()
