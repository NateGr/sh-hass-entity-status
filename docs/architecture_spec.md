# Architecture Specification — SmartHass Entity Status

## Overview

SmartHass Entity Status is a Home Assistant custom integration that monitors entity availability across the entire HA instance and provides configurable suppression so that "expected" unavailability (e.g. a device under maintenance) doesn't pollute dashboards or automations.

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
│              │  Entities (4 sensors + 1 button)      │           │
│              │  unsuppressed_unavailable_count       │           │
│              │  suppressed_unavailable_count         │           │
│              │  unsuppressed_unavailable_list        │           │
│              │  suppressed_unavailable_list          │           │
│              │  refresh_registry button              │           │
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
| `sensor.py` | 4 `CoordinatorEntity` sensors that read `coordinator.data` |
| `button.py` | 1 button entity for immediate registry rebuild |
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
              ├── map unavailable entities to either
              │   valid device IDs or orphaned entities
              │
              ├── split devices into
              │   unsuppressed_unavailable_devices
              │   suppressed_unavailable_devices
              │
              ├── split orphaned entities into
              │   unsuppressed_orphaned_unavailable_entities
              │   suppressed_orphaned_unavailable_entities
              │
              └── publish 2 category totals and 2 category lists
```

---

## Suppression Logic Flow

```
Unavailable entity
                                │
                                ▼
Has valid parent device?
        YES ──► device bucket
                                                │
                                                ▼
                        Device has ignore label?
                                YES ──► suppressed_unavailable_devices
                                NO  ──► unsuppressed_unavailable_devices

        NO  ──► orphan bucket
                                                │
                                                ▼
                        Entity has ignore label?
                                YES ──► suppressed_orphaned_unavailable_entities
                                NO  ──► unsuppressed_orphaned_unavailable_entities
```

---

## Entity Architecture

Sensors inherit from both `CoordinatorEntity` and `SensorEntity`. The button inherits from `ButtonEntity`.

Coordinator output keys:

- `unsuppressed_unavailable_count`
- `suppressed_unavailable_count`
- `unsuppressed_unavailable_devices`
- `suppressed_unavailable_devices`
- `unsuppressed_orphaned_unavailable_entities`
- `suppressed_orphaned_unavailable_entities`

The list sensors expose the full corresponding device and orphaned-entity collections as attributes. Device records exposed to the sensors intentionally omit child `entities` lists.

All entities publish shared `DeviceInfo`, so Home Assistant groups them under one integration device page.

---

## Service Architecture

Services are registered under the `sh_entity_status` domain. They iterate over all loaded config entries and call the relevant coordinator method. Services are registered once on first entry setup and removed when the last entry is unloaded.

Service metadata is provided via `services.yaml` so services show names/descriptions in the HA UI.
