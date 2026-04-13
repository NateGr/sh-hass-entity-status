"""Sensor platform for SmartHass Entity Status integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_ID_PREFIX, INTEGRATION_NAME
from .coordinator import SHEntityStatusCoordinator

# Sensor short names — ENTITY_ID_PREFIX is prepended at runtime so that all
# entity_ids share a common namespace (e.g. sensor.sh_entity_status_unavailable_count).
# To rename sensors: change the "name" value here; the prefix is controlled via
# ENTITY_ID_PREFIX in const.py.
_SENSOR_DESCRIPTIONS = [
    {
        "key": "unsuppressed_unavailable_count",
        "name": "Unsuppressed Unavailable Count",
        "icon": "mdi:alert-circle-outline",
    },
    {
        "key": "suppressed_unavailable_count",
        "name": "Suppressed Unavailable Count",
        "icon": "mdi:bell-off-outline",
    },
    {
        "key": "unsuppressed_unavailable_list",
        "name": "Unsuppressed Unavailable List",
        "icon": "mdi:format-list-bulleted",
    },
    {
        "key": "suppressed_unavailable_list",
        "name": "Suppressed Unavailable List",
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
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=INTEGRATION_NAME,
            manufacturer="SmartHass",
            model="Entity Status Monitor",
        )
        # Explicitly stamp the entity_id so all sensors share the ENTITY_ID_PREFIX
        # namespace regardless of what friendly name is set above.
        self.entity_id = (
            f"sensor.{ENTITY_ID_PREFIX}_{self._key}"
            if ENTITY_ID_PREFIX
            else f"sensor.{self._key}"
        )

    @property
    def native_value(self) -> int:
        """Return the sensor state (always a count)."""
        data = self.coordinator.data or {}
        key = self._key

        if key in (
            "unsuppressed_unavailable_count",
            "suppressed_unavailable_count",
        ):
            return int(data.get(key, 0))
        if key == "unsuppressed_unavailable_list":
            return len(data.get("unsuppressed_unavailable_devices", [])) + len(
                data.get("unsuppressed_orphaned_unavailable_entities", [])
            )
        if key == "suppressed_unavailable_list":
            return len(data.get("suppressed_unavailable_devices", [])) + len(
                data.get("suppressed_orphaned_unavailable_entities", [])
            )
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes for list sensors."""
        data = self.coordinator.data or {}
        if self._key == "unsuppressed_unavailable_list":
            return {
                "unsuppressed_unavailable_devices": data.get(
                    "unsuppressed_unavailable_devices", []
                ),
                "unsuppressed_orphaned_unavailable_entities": data.get(
                    "unsuppressed_orphaned_unavailable_entities", []
                ),
            }
        if self._key == "suppressed_unavailable_list":
            return {
                "suppressed_unavailable_devices": data.get(
                    "suppressed_unavailable_devices", []
                ),
                "suppressed_orphaned_unavailable_entities": data.get(
                    "suppressed_orphaned_unavailable_entities", []
                ),
            }
        return None
