"""Coordinator for SmartHass Entity Status integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.helpers.label_registry import EVENT_LABEL_REGISTRY_UPDATED
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_IGNORE_LABEL,
    CONF_POLL_INTERVAL,
    CONF_REFRESH_INTERVAL,
    DEFAULT_IGNORE_LABEL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SHEntityStatusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that tracks unavailable entities with suppression logic."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        options = {**config_entry.data, **config_entry.options}

        poll_interval = int(options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
        self._refresh_interval = int(
            options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        )
        self._ignore_label: str = options.get(CONF_IGNORE_LABEL, DEFAULT_IGNORE_LABEL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )

        # In-memory registry hierarchy
        self._devices: dict[str, dict] = {}
        self._orphan_entities: list[dict] = []

        # Cleanup handles
        self._registry_refresh_unsub = None
        self._event_unsubs: list = []

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Start periodic registry refresh and event listeners."""
        await self._async_refresh_registry()

        # Periodic registry refresh
        self._registry_refresh_unsub = async_track_time_interval(
            self.hass,
            self._handle_registry_refresh_interval,
            timedelta(minutes=self._refresh_interval),
        )

        # Listen for registry changes
        self._event_unsubs.append(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED,
                self._handle_registry_event,
            )
        )
        self._event_unsubs.append(
            self.hass.bus.async_listen(
                dr.EVENT_DEVICE_REGISTRY_UPDATED,
                self._handle_registry_event,
            )
        )
        self._event_unsubs.append(
            self.hass.bus.async_listen(
                EVENT_LABEL_REGISTRY_UPDATED,
                self._handle_registry_event,
            )
        )

    async def async_teardown(self) -> None:
        """Cancel listeners and timers."""
        if self._registry_refresh_unsub is not None:
            self._registry_refresh_unsub()
            self._registry_refresh_unsub = None
        for unsub in self._event_unsubs:
            unsub()
        self._event_unsubs.clear()

    # ------------------------------------------------------------------
    # Registry refresh
    # ------------------------------------------------------------------

    @callback
    def _handle_registry_refresh_interval(self, _now: Any) -> None:
        """Scheduled handler — schedule coroutine on the event loop."""
        self.hass.async_create_task(self._async_refresh_registry())

    @callback
    def _handle_registry_event(self, event: Event) -> None:
        """Triggered on entity/device registry updates."""
        self.hass.async_create_task(self._async_refresh_registry())

    async def _async_refresh_registry(self) -> None:
        """Rebuild the in-memory device/entity hierarchy from HA registries."""
        entity_reg = er.async_get(self.hass)
        device_reg = dr.async_get(self.hass)
        area_reg = ar.async_get(self.hass)
        label_reg = lr.async_get(self.hass)

        # Build a list of all known label IDs from the registry.
        all_label_ids = [label.label_id for label in label_reg.labels.values()]

        devices: dict[str, dict] = {}
        orphan_entities: list[dict] = []

        for entity_entry in entity_reg.entities.values():
            entity_labels = list(entity_entry.labels or [])
            entity_label_set = set(entity_labels)
            # Include every known label with explicit true/false assignment state.
            entity_label_map = {
                label_id: label_id in entity_label_set for label_id in all_label_ids
            }
            entity_area_id = entity_entry.area_id
            entity_area_name = ""
            if entity_area_id and entity_area_id in area_reg.areas:
                entity_area_name = area_reg.areas[entity_area_id].name

            entity_dict = {
                "entity_id": entity_entry.entity_id,
                "name": entity_entry.name
                or entity_entry.original_name
                or entity_entry.entity_id,
                "device_id": entity_entry.device_id,
                "area_id": entity_area_id,
                "area_name": entity_area_name,
                "labels": entity_labels,
                "label_map": entity_label_map,
            }

            if entity_entry.device_id is None:
                orphan_entities.append(entity_dict)
                continue

            device_id = entity_entry.device_id
            if device_id not in devices:
                dev = device_reg.devices.get(device_id)
                if dev is None:
                    orphan_entities.append(entity_dict)
                    continue

                dev_labels = list(dev.labels or [])
                dev_label_set = set(dev_labels)
                # Include every known label with explicit true/false assignment state.
                dev_label_map = {
                    label_id: label_id in dev_label_set for label_id in all_label_ids
                }
                dev_area_id = dev.area_id
                dev_area_name = ""
                if dev_area_id and dev_area_id in area_reg.areas:
                    dev_area_name = area_reg.areas[dev_area_id].name

                devices[device_id] = {
                    "id": device_id,
                    # Prefer user-assigned name so it matches what users see in the HA UI.
                    "name": dev.name_by_user or dev.name or device_id,
                    "area_id": dev_area_id,
                    "area_name": dev_area_name,
                    "labels": dev_labels,
                    "label_map": dev_label_map,
                    "entities": [],
                }

            devices[device_id]["entities"].append(entity_dict)

        self._devices = devices
        self._orphan_entities = orphan_entities
        _LOGGER.debug(
            "Registry refreshed: %d devices, %d orphan entities",
            len(devices),
            len(orphan_entities),
        )
        # Trigger a fresh poll after registry rebuild
        await self.async_request_refresh()

    # ------------------------------------------------------------------
    # Unavailability poll  (DataUpdateCoordinator callback)
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll for unavailable entities and apply suppression logic."""
        try:
            return self._compute_unavailable()
        except Exception as exc:
            raise UpdateFailed(f"Error computing unavailable entities: {exc}") from exc

    def _compute_unavailable(self) -> dict[str, Any]:
        """
        Compute unsuppressed/suppressed unavailable entities.

        Suppression precedence:
        1. Entity-level: entity carries the ignore label → suppressed.
        2. Device-level: after entity filter, if device carries the ignore label
           → ALL remaining unavailable entities on that device are suppressed.

        TODO: Add filter criteria (area, device class, entity type).
        TODO: Add temporary/time-based suppression.
        TODO: Add dynamic label picker support.
        """
        ignore_label = self._ignore_label

        # Collect all currently unavailable entity IDs
        unavailable_ids: set[str] = {
            state.entity_id
            for state in self.hass.states.async_all()
            if state.state == STATE_UNAVAILABLE
        }

        if not unavailable_ids:
            return {
                "unsuppressed_entities": [],
                "suppressed_entities": [],
                "unsuppressed_devices": [],
                "suppressed_devices": [],
            }

        # Build a lookup: entity_id → entity_dict
        entity_lookup: dict[str, dict] = {}
        for device in self._devices.values():
            for ent in device["entities"]:
                entity_lookup[ent["entity_id"]] = ent
        for ent in self._orphan_entities:
            entity_lookup[ent["entity_id"]] = ent

        unsuppressed_entities: list[dict] = []
        suppressed_entities: list[dict] = []

        # --- Step 1: entity-level filter ---
        after_entity_filter: list[dict] = []
        for eid in unavailable_ids:
            ent = entity_lookup.get(eid)
            if ent is None:
                # Unknown entity — treat as unsuppressed orphan
                ent = {
                    "entity_id": eid,
                    "name": eid,
                    "device_id": None,
                    "area_id": None,
                    "area_name": "",
                    "labels": [],
                    "label_map": {},
                }
            if ent.get("label_map", {}).get(ignore_label, False):
                suppressed_entities.append(ent)
            else:
                after_entity_filter.append(ent)

        # --- Step 2: device-level filter ---
        # Group remaining unavailable entities by device
        by_device: dict[str, list[dict]] = {}
        no_device: list[dict] = []
        for ent in after_entity_filter:
            did = ent.get("device_id")
            if did:
                by_device.setdefault(did, []).append(ent)
            else:
                no_device.append(ent)

        unsuppressed_devices: list[dict] = []
        suppressed_devices: list[dict] = []

        for device_id, ents in by_device.items():
            device = self._devices.get(device_id)
            if device and device.get("label_map", {}).get(ignore_label, False):
                # Suppress entire device
                suppressed_entities.extend(ents)
                suppressed_devices.append(device)
            else:
                unsuppressed_entities.extend(ents)
                if device:
                    unsuppressed_devices.append(device)

        # Orphan entities (no device) are always unsuppressed at this stage
        unsuppressed_entities.extend(no_device)

        return {
            "unsuppressed_entities": unsuppressed_entities,
            "suppressed_entities": suppressed_entities,
            "unsuppressed_devices": unsuppressed_devices,
            "suppressed_devices": suppressed_devices,
        }

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def async_refresh_registry(self) -> None:
        """Public API to trigger a registry refresh (used by service)."""
        await self._async_refresh_registry()
