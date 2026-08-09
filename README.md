# SmartHass Entity Status
[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![CI](https://github.com/NateGr/sh-hass-entity-status/actions/workflows/ci.yml/badge.svg)](https://github.com/NateGr/sh-hass-entity-status/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/release/NateGr/sh-hass-entity-status.svg?style=flat-square)](https://github.com/NateGr/sh-hass-entity-status/releases)
[![GitHub Downloads](https://img.shields.io/github/downloads/NateGr/sh-hass-entity-status/total.svg?style=flat-square)](https://github.com/NateGr/sh-hass-entity-status/releases)
[![License](https://img.shields.io/github/license/NateGr/sh-hass-entity-status)](LICENSE)

A Home Assistant custom integration that monitors entity availability across your entire HA instance and exposes configurable **suppression** — so that "expected" unavailability (a device under maintenance, a sensor you don't care about) doesn't pollute your dashboards or trigger false alerts.

---

## Minimum HA Version

**2026.3.0**

---

## Installation

### Via HACS (recommended)

1. In HACS, go to **Integrations → Custom Repositories**.
2. Add `https://github.com/NateGr/sh-hass-entity-status` (type: Integration).
3. Install **SmartHass Entity Status** and restart Home Assistant.

### Manual

1. Download or clone this repository.
2. Copy `custom_components/sh_entity_status/` into your HA config's `custom_components/` directory.
3. Restart Home Assistant.

---

## What It Does

- Continuously polls all HA entities for `unavailable` state.
- Classifies unavailable items into **unsuppressed** (needs attention) and **suppressed** (deliberately ignored) categories.
- Tracks unavailable **devices** and **orphaned entities** (entities with no parent device, such as Helpers) separately.
- Exposes sensors for automation, dashboards, and notifications based on the real health of your devices.
- Provides a `display_name` attribute for devices and entities, formatted as `Name (Area)` if an area exists, otherwise just `Name`.

### Suppression Model

Suppression is controlled by a configurable HA **label** (default: `ignore_unavailable`).

| Applied to             | Effect                                     |
| ---------------------- | ------------------------------------------ |
| A **device**           | That device appears in the suppressed list |
| An **orphaned entity** | That entity appears in the suppressed list |

### Orphaned Entities

An entity is considered **orphaned** if it has no valid parent device — for example a Helper (`input_boolean`, `input_text`, etc.) or an entity whose device has been removed from the registry. Orphaned entities are tracked separately from device-linked entities.

---

## Configuration

After installation, go to **Settings → Devices & Services → Add Integration** and search for **SmartHass Entity Status**.

| Field                      | Default                   | Description                                                |
| -------------------------- | ------------------------- | ---------------------------------------------------------- |
| Integration name           | `SmartHass Entity Status` | Display name for this entry                                |
| Ignore label name          | `ignore_unavailable`      | HA label slug that marks entities/devices to suppress      |
| Refresh interval (minutes) | `60`                      | How often to rebuild the registry hierarchy. Must be >= 1. |
| Poll interval (seconds)    | `30`                      | How often to check for unavailable entities. Must be >= 5. |

All options are editable post-setup via the **Configure** button on the integration card.

---

## Entities

All entity IDs are prefixed with `sh_entity_status_`. All entities appear together under a single **SmartHass Entity Status** device in Settings → Devices & Services.

### Button

| Entity ID                                  | Description                                                        |
| ------------------------------------------ | ------------------------------------------------------------------ |
| `button.sh_entity_status_refresh_registry` | Immediately rebuilds the internal device/entity registry hierarchy |

### Count Sensors

- `sensor.sh_entity_status_unsuppressed_unavailable_count`
- `sensor.sh_entity_status_suppressed_unavailable_count`

**State:**

- The total number of unavailable devices and orphaned entities (suppressed or unsuppressed).

**Attributes:**

- `devices_count`: Integer. The count of unavailable devices (matching suppressed/unsuppressed)
- `entities_count`: Integer. The count of unavailable orphaned entities (matching suppressed/unsuppressed)

This naming avoids confusion with the list sensors, which use `devices` and `entities` as lists.

### List Sensors

- `sensor.sh_entity_status_unsuppressed_unavailable_list`
- `sensor.sh_entity_status_suppressed_unavailable_list`

**State:**

- The total number of unavailable devices and orphaned entities (suppressed or unsuppressed).

**Attributes:**

- `devices`: List of unavailable devices
- `entities`: List of unavailable orphaned entities

### Attributes on `unsuppressed_unavailable_list`

```yaml
devices:
  - id: abc123
    name: Philips Hue Bulb
    area_id: living_room
    area_name: Living Room
    labels: []
    label_map:
      ignore_unavailable: false
entities:
  - entity_id: input_boolean.vacation_mode
    name: Vacation Mode
    device_id: null
    area_id: null
    area_name: ""
    labels: []
    label_map:
      ignore_unavailable: false
```

### Attributes on `suppressed_unavailable_list`

Same structure with `devices` and `entities` keys (the sensor **state** — `suppressed` — distinguishes the context).

---

## Services

| Service                             | Description                                                                                         |
| ----------------------------------- | --------------------------------------------------------------------------------------------------- |
| `sh_entity_status.refresh_registry` | Rebuild the in-memory device/entity/label hierarchy immediately (also available as a button entity) |
| `sh_entity_status.poll_unavailable` | Immediately re-poll for unavailable entities                                                        |
| `sh_entity_status.reload`           | Reload all SmartHass Entity Status config entries                                                   |

Services are also visible and callable from **Developer Tools → Actions** in the HA UI.

---

## Using Suppression Labels

### Suppress a device

1. Open the device in HA.
2. Go to **Settings** and add the label `ignore_unavailable` (or your custom label name).
3. The device will move from the unsuppressed list to the suppressed list on the next poll.

### Suppress an orphaned entity

1. Open the entity in HA.
2. Go to **Settings** and add the label `ignore_unavailable`.
3. The entity will move from the unsuppressed list to the suppressed list on the next poll.

---

## Automation Example

```yaml
automation:
  - alias: Alert on new unavailable items
    trigger:
      - platform: numeric_state
        entity_id: sensor.sh_entity_status_unsuppressed_unavailable_count
        above: 0
    action:
      - service: notify.mobile_app_my_phone
        data:
          message: >
            {{ states('sensor.sh_entity_status_unsuppressed_unavailable_count') }} unavailable items need attention.
```

### Template: list unsuppressed items

```yaml
{% set devices = state_attr('sensor.sh_entity_status_unsuppressed_unavailable_list', 'devices') or [] %}
{% set orphans = state_attr('sensor.sh_entity_status_unsuppressed_unavailable_list', 'entities') or [] %}
Devices:
{% for d in devices %}  - {{ d.name }} ({{ d.area_name or 'no area' }})
{% endfor %}
Orphaned entities:
{% for e in orphans %}  - {{ e.name }} ({{ e.entity_id }})
{% endfor %}
```

---

## Roadmap

- Temporary / time-based suppression (suppress for N minutes)
- Multiple ignore labels with ANY / ALL logic
- Dynamic label picker in the config flow UI
- Filter monitoring scope by area, device class, or entity type
- Custom Lovelace card for dashboard display

---

## Contributing

If you want to submit a pull request, use this flow:

1. Fork this repository.
2. Create a branch from `main` in your fork.
3. Make your change.
4. Run local checks:

  ```bash
  ruff check .
  python -m pytest tests/ -v
  ```

5. Open a pull request with a short summary of the change.

If your change affects behavior, update tests and user-facing docs in the same pull request.
Review the repository license before submitting changes. See [`LICENSE`](LICENSE).

For local setup and release workflow details, see [`docs/developer_spec.md`](docs/developer_spec.md).
