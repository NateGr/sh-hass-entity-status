"""Coordinator for SmartHass Entity Status integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers import (
    label_registry as lr,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.label_registry import EVENT_LABEL_REGISTRY_UPDATED
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

_HEARTBEAT_INTERVAL = timedelta(seconds=60)


def _format_duration(td: timedelta) -> str:
    """Format a timedelta as a human-readable string, e.g. '2h 15m' or '45s'."""
    total_seconds = int(td.total_seconds())
    if total_seconds <= 0:
        return "0s"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


class SHEntityStatusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that tracks unavailable devices and orphaned entities."""

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

        # Diagnostic timestamps
        self._last_registry_refresh: datetime | None = None
        self._last_status_poll: datetime | None = None

        # Downtime tracking: entity_id → when it first became unavailable
        self._downtime_start: dict[str, datetime] = {}
        self._last_downtime_duration: str | None = None

        # Cleanup handles
        self._registry_refresh_unsub: Callable[[], None] | None = None
        self._heartbeat_unsub: Callable[[], None] | None = None
        self._event_unsubs: list[Callable[[], None]] = []

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

        # Heartbeat timer — updates independently of the poll interval
        self._heartbeat_unsub = async_track_time_interval(
            self.hass,
            self._handle_heartbeat,
            _HEARTBEAT_INTERVAL,
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
        if self._heartbeat_unsub is not None:
            self._heartbeat_unsub()
            self._heartbeat_unsub = None
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
    def _handle_registry_event(self, event: Event[Any]) -> None:
        """Triggered on entity/device registry updates."""
        self.hass.async_create_task(self._async_refresh_registry())

    @callback
    def _handle_heartbeat(self, _now: Any) -> None:
        """Periodic heartbeat — merge updated timestamp into current coordinator data."""
        current = dict(self.data) if self.data else {}
        current["heartbeat"] = "active"
        self.async_set_updated_data(current)

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

            # Compose display_name as 'Name (Area)' if area exists, else just 'Name'
            entity_base_name = (
                entity_entry.name
                or entity_entry.original_name
                or entity_entry.entity_id
            )
            if entity_area_name:
                display_name = f"{entity_base_name} ({entity_area_name})"
            else:
                display_name = entity_base_name

            entity_dict = {
                "entity_id": entity_entry.entity_id,
                "name": entity_base_name,
                "display_name": display_name,
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

                # Compose display_name as 'Name (Area)' if area exists, else just 'Name'
                device_base_name = dev.name_by_user or dev.name or device_id
                if dev_area_name:
                    device_display_name = f"{device_base_name} ({dev_area_name})"
                else:
                    device_display_name = device_base_name

                devices[device_id] = {
                    "id": device_id,
                    "name": device_base_name,
                    "display_name": device_display_name,
                    "area_id": dev_area_id,
                    "area_name": dev_area_name,
                    "labels": dev_labels,
                    "label_map": dev_label_map,
                    "entities": [],
                }

            devices[device_id]["entities"].append(entity_dict)

        self._devices = devices
        self._orphan_entities = orphan_entities
        self._last_registry_refresh = datetime.now(timezone.utc)
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
        """Poll for unavailable entities and compute integration metrics."""
        try:
            result = self._compute_unavailable()
            self._last_status_poll = datetime.now(timezone.utc)
            result["last_registry_refresh"] = self._last_registry_refresh
            result["last_status_poll"] = self._last_status_poll
            return result
        except Exception as exc:
            raise UpdateFailed(f"Error computing unavailable entities: {exc}") from exc

    def _compute_unavailable(self) -> dict[str, Any]:
        """Compute unavailable buckets and expose simple suppressed/unsuppressed views."""
        ignore_label = self._ignore_label

        # Collect all currently unavailable entity IDs
        unavailable_ids: set[str] = {
            state.entity_id
            for state in self.hass.states.async_all()
            if state.state == STATE_UNAVAILABLE
        }

        # Compute total registry counts (independent of unavailability)
        total_devices = len(self._devices)
        total_entities = sum(
            len(d.get("entities", [])) for d in self._devices.values()
        ) + len(self._orphan_entities)

        # Update downtime tracking
        now = datetime.now(timezone.utc)
        # Start tracking newly unavailable entities
        for eid in unavailable_ids:
            if eid not in self._downtime_start:
                self._downtime_start[eid] = now
        # Handle recoveries — compute duration for entities that came back online
        recovered = set(self._downtime_start.keys()) - unavailable_ids
        if recovered:
            max_duration = max(now - self._downtime_start[eid] for eid in recovered)
            self._last_downtime_duration = _format_duration(max_duration)
            for eid in recovered:
                del self._downtime_start[eid]

        _base = {
            "total_devices_count": total_devices,
            "total_entities_count": total_entities,
            "heartbeat": "active",
        }

        if not unavailable_ids:
            return {
                "unsuppressed_unavailable_count": 0,
                "suppressed_unavailable_count": 0,
                "unsuppressed_unavailable_devices": [],
                "suppressed_unavailable_devices": [],
                "unsuppressed_orphaned_unavailable_entities": [],
                "suppressed_orphaned_unavailable_entities": [],
                **_base,
            }

        # Build a lookup: entity_id → entity_dict
        entity_lookup: dict[str, dict] = {}
        for device in self._devices.values():
            for ent in device["entities"]:
                entity_lookup[ent["entity_id"]] = ent
        for ent in self._orphan_entities:
            entity_lookup[ent["entity_id"]] = ent

        unavailable_device_ids: set[str] = set()
        unsuppressed_orphaned_unavailable_entities: list[dict] = []
        suppressed_orphaned_unavailable_entities: list[dict] = []

        # Collect unavailable devices and orphaned unavailable entities.
        for eid in sorted(unavailable_ids):
            ent = entity_lookup.get(eid)
            if ent is None:
                # Unknown entity — treat as orphaned.
                ent = {
                    "entity_id": eid,
                    "name": eid,
                    "device_id": None,
                    "area_id": None,
                    "area_name": "",
                    "labels": [],
                    "label_map": {},
                }

            device_id = ent.get("device_id")
            if device_id and device_id in self._devices:
                unavailable_device_ids.add(device_id)
            else:
                if ent.get("label_map", {}).get(ignore_label, False):
                    suppressed_orphaned_unavailable_entities.append(ent)
                else:
                    unsuppressed_orphaned_unavailable_entities.append(ent)

        def _strip_entities(device: dict) -> dict:
            return {k: v for k, v in device.items() if k != "entities"}

        unavailable_devices = [
            _strip_entities(self._devices[device_id])
            for device_id in sorted(unavailable_device_ids)
            if device_id in self._devices
        ]
        suppressed_unavailable_devices = [
            device
            for device in unavailable_devices
            if device.get("label_map", {}).get(ignore_label, False)
        ]
        unsuppressed_unavailable_devices = [
            device
            for device in unavailable_devices
            if not device.get("label_map", {}).get(ignore_label, False)
        ]

        return {
            "unsuppressed_unavailable_count": len(unsuppressed_unavailable_devices)
            + len(unsuppressed_orphaned_unavailable_entities),
            "suppressed_unavailable_count": len(suppressed_unavailable_devices)
            + len(suppressed_orphaned_unavailable_entities),
            "unsuppressed_unavailable_devices": unsuppressed_unavailable_devices,
            "suppressed_unavailable_devices": suppressed_unavailable_devices,
            "unsuppressed_orphaned_unavailable_entities": (
                unsuppressed_orphaned_unavailable_entities
            ),
            "suppressed_orphaned_unavailable_entities": (
                suppressed_orphaned_unavailable_entities
            ),
            **_base,
        }

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def async_refresh_registry(self) -> None:
        """Public API to trigger a registry refresh (used by service)."""
        await self._async_refresh_registry()
