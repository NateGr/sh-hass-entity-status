"""Sensor platform for SmartHass Entity Status integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SHEntityStatusCoordinator

_SENSOR_DESCRIPTIONS = [
    {
        "key": "unavailable_count",
        "name": "Unavailable Count",
        "icon": "mdi:alert-circle-outline",
    },
    {
        "key": "unsuppressed_unavailable_count",
        "name": "Unsuppressed Unavailable Count",
        "icon": "mdi:alert-circle",
    },
    {
        "key": "suppressed_count",
        "name": "Suppressed Count",
        "icon": "mdi:bell-off-outline",
    },
    {
        "key": "unavailable_list",
        "name": "Unavailable List",
        "icon": "mdi:format-list-bulleted",
    },
    {
        "key": "suppressed_list",
        "name": "Suppressed List",
        "icon": "mdi:format-list-checks",
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartHass Entity Status sensors from a config entry."""
    coordinator: SHEntityStatusCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SHEntityStatusSensor(coordinator, entry, desc)
            for desc in _SENSOR_DESCRIPTIONS
        ]
    )


class SHEntityStatusSensor(CoordinatorEntity[SHEntityStatusCoordinator], SensorEntity):
    """A single SmartHass Entity Status sensor."""

    def __init__(
        self,
        coordinator: SHEntityStatusCoordinator,
        entry: ConfigEntry,
        description: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = description["key"]
        self._attr_name = description["name"]
        self._attr_icon = description["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{DOMAIN}_{self._key}"
        self._entry_id = entry.entry_id

    @property
    def native_value(self) -> int:
        """Return the sensor state (always a count)."""
        data = self.coordinator.data or {}
        key = self._key

        if key == "unavailable_count":
            return len(data.get("unsuppressed_entities", [])) + len(
                data.get("suppressed_entities", [])
            )
        if key == "unsuppressed_unavailable_count":
            return len(data.get("unsuppressed_entities", []))
        if key == "suppressed_count":
            return len(data.get("suppressed_entities", []))
        if key == "unavailable_list":
            return len(data.get("unsuppressed_entities", []))
        if key == "suppressed_list":
            return len(data.get("suppressed_entities", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes for list sensors."""
        data = self.coordinator.data or {}
        if self._key == "unavailable_list":
            return {
                "unsuppressed_entities": data.get("unsuppressed_entities", []),
                "unsuppressed_devices": data.get("unsuppressed_devices", []),
            }
        if self._key == "suppressed_list":
            return {
                "suppressed_entities": data.get("suppressed_entities", []),
                "suppressed_devices": data.get("suppressed_devices", []),
            }
        return None
