# Architecture Specification — SH Entity Status

## Overview

SH Entity Status is a Home Assistant custom integration that monitors entity availability across the entire HA instance and provides configurable suppression so that "expected" unavailability (e.g. a device under maintenance) doesn't pollute dashboards or automations.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Home Assistant Core                                            │
│                                                                 │
│  Entity Registry ──┐                                            │
│  Device Registry ──┤──► SHEntityStatusCoordinator              │
│  Area Registry  ──┤         │                                   │
│  Label Registry ──┘         │  ┌──────────────────────────┐    │
│                             │  │  In-memory hierarchy      │    │
│  hass.states ──────────────►│  │  devices{} + orphans[]   │    │
│                             │  └──────────────────────────┘    │
│  HA Event Bus ─────────────►│         │                         │
│  (entity/device updated)    │         ▼                         │
│                             │  _compute_unavailable()           │
│                             │         │                         │
│                             ▼         ▼                         │
│              ┌──────────────────────────────────────┐           │
│              │  CoordinatorEntity (5 sensors)        │           │
│              │  unavailable_count                    │           │
│              │  unsuppressed_unavailable_count        │           │
│              │  suppressed_count                     │           │
│              │  unavailable_list (+ attributes)      │           │
│              │  suppressed_list  (+ attributes)      │           │
│              └──────────────────────────────────────┘           │
│                                                                 │
│              Services: refresh_registry | poll_unavailable      │
│                        | reload                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility |
|---|---|
| `const.py` | Single source of truth for domain slug and config key names / defaults |
| `config_flow.py` | UI wizard for initial setup and options editing; voluptuous schema validation |
| `coordinator.py` | Registry refresh, unavailability poll, suppression logic, event subscriptions |
| `sensor.py` | 5 `CoordinatorEntity` sensors that read `coordinator.data` |
| `services.py` | Registers/unregisters 3 HA services |
| `__init__.py` | Wires everything together: setup, teardown, platform forwarding |

---

## Data Flow: Registry Refresh

```
async_setup()
    │
    ├──► async_track_time_interval  ──► (every N minutes)
    │                                       │
    ├──► hass.bus.async_listen               │
    │    entity_registry_updated  ──────────►│
    │    device_registry_updated  ──────────►│
    │                                       ▼
    └───────────────────────────── _async_refresh_registry()
                                        │
                                        ├── entity_registry.entities
                                        ├── device_registry.devices
                                        ├── area_registry.areas
                                        └── label_registry.labels
                                             │
                                             ▼
                                     self._devices  (dict)
                                     self._orphan_entities  (list)
                                             │
                                             └──► async_request_refresh()
```

---

## Data Flow: Unavailability Poll

```
DataUpdateCoordinator._async_update_data()   (every poll_interval seconds)
    │
    └──► _compute_unavailable()
              │
              ├── hass.states.async_all() → filter state == "unavailable"
              │
              ├── Step 1 (entity-level suppression):
              │   for each unavailable entity:
              │     if entity.label_map contains ignore_label → suppressed_entities
              │     else → after_entity_filter
              │
              ├── Step 2 (device-level suppression):
              │   group after_entity_filter by device_id
              │   for each device:
              │     if device.label_map contains ignore_label →
              │         all device entities → suppressed_entities
              │         device → suppressed_devices
              │     else →
              │         entities → unsuppressed_entities
              │         device → unsuppressed_devices
              │
              └── orphan entities (no device) → unsuppressed_entities
```

---

## Suppression Logic Flow

```
Unavailable entity
        │
        ▼
Entity has ignore label?
  YES ──► suppressed_entities
  NO  ──► group by device
              │
              ▼
        Device has ignore label?
          YES ──► suppressed_entities + suppressed_devices
          NO  ──► unsuppressed_entities + unsuppressed_devices
```

---

## Sensor Architecture

All 5 sensors inherit from both `CoordinatorEntity` and `SensorEntity`. They read from `coordinator.data` which is a dict with keys:

- `unsuppressed_entities` — list of entity dicts
- `suppressed_entities` — list of entity dicts
- `unsuppressed_devices` — list of device dicts
- `suppressed_devices` — list of device dicts

The `native_value` for every sensor is an integer count. The `extra_state_attributes` on `unavailable_list` and `suppressed_list` sensors expose the full entity/device detail dicts.

---

## Service Architecture

Services are registered under the `sh_entity_status` domain. They iterate over all loaded config entries and call the relevant coordinator method. Services are registered once on first entry setup and removed when the last entry is unloaded.
