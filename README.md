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

### List Sensors

- `sensor.sh_entity_status_unsuppressed_list`
- `sensor.sh_entity_status_suppressed_list`

**State:**

- The total number of unavailable devices and orphaned entities (suppressed or unsuppressed).

**Attributes:**

- `devices`: List of unavailable devices
- `entities`: List of unavailable orphaned entities
- `devices_count`: Number of unavailable devices
- `entities_count`: Number of unavailable orphaned entities

### Attributes on `unsuppressed_list`

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

### Attributes on `suppressed_list`

Same structure with `devices` and `entities` keys (the sensor **state** — `suppressed` — distinguishes the context).

---

## Services

| Service                             | Description                                                                                         |
| ----------------------------------- | --------------------------------------------------------------------------------------------------- |
| `sh_entity_status.refresh_registry` | Rebuild the in-memory device/entity/label hierarchy immediately (also available as a button entity) |
| `sh_entity_status.poll_unavailable` | Immediately re-poll for unavailable entities                                                        |
| `sh_entity_status.reload`           | Reload all SmartHass Entity Status config entries                                                   |
| `sh_entity_status.get_registry`     | Return the complete mapped device/entity hierarchy as response data (no entity storage)            |

Services are also visible and callable from **Developer Tools → Actions** in the HA UI.

### Export all mapped devices and entities

`sh_entity_status.get_registry` is a **response-only action** with no input fields.
It returns a JSON-compatible object directly to the caller, without creating an
entity, updating sensor attributes, or writing the document to Home Assistant's
state/history.

The response includes **all mapped items**, regardless of availability or
suppression, including disabled registered entities. Each mapped device contains
its entities; entities without a valid parent device are in `orphan_entities`.
Devices without registered entities and state-only entities outside the entity
registry are not part of the integration's mapping.

This is a snapshot of the existing in-memory mapping, not a live state export.
For a fresh registry snapshot, call `sh_entity_status.refresh_registry` first and
wait for it to finish. `last_registry_refresh` is an ISO 8601 UTC timestamp (or
`null` if the mapping has not yet been built).

#### Home Assistant action

Capture the response in an automation or script:

```yaml
- action: sh_entity_status.get_registry
  response_variable: mapped_registry
```

The result is available as `mapped_registry.entries`. Calls must request response
data; calling this action without requesting a response is rejected.

#### REST API / Node-RED

Use Home Assistant's existing authenticated service API:

```text
POST /api/services/sh_entity_status/get_registry?return_response
Content-Type: application/json

{}
```

In Node-RED, configure an **HTTP Request** node with this URL on your Home
Assistant server, method `POST`, an empty JSON object as the request payload, and
the content-type header above. Set the `Authorization` header to `Bearer` followed
by a space and your Home Assistant access token. Configure the response as a parsed
JSON object. Keep the access token in secure credentials, not exported flow JSON.
Use HTTPS when accessing Home Assistant over an untrusted network.

Home Assistant wraps the action response in `service_response`; the mapping is
therefore at **`msg.payload.service_response`**. The `changed_states` array is
normally empty because this action does not change entity states. Omitting
`?return_response` results in HTTP 400.

#### Response format

The action response (the REST API's `service_response` object) has this shape:

```json
{
  "schema_version": 1,
  "entries": {
    "example_config_entry_id": {
      "last_registry_refresh": "2026-03-01T12:00:00+00:00",
      "devices_count": 1,
      "entities_count": 2,
      "devices": [
        {
          "id": "abc123",
          "name": "Kitchen Light",
          "display_name": "Kitchen Light (Kitchen)",
          "area_id": "kitchen",
          "area_name": "Kitchen",
          "labels": [],
          "label_map": {"ignore_unavailable": false},
          "entities": [
            {
              "entity_id": "light.kitchen",
              "name": "Kitchen Light",
              "display_name": "Kitchen Light",
              "device_id": "abc123",
              "area_id": null,
              "area_name": "",
              "labels": [],
              "label_map": {"ignore_unavailable": false}
            }
          ]
        }
      ],
      "orphan_entities": [
        {
          "entity_id": "input_boolean.vacation_mode",
          "name": "Vacation Mode",
          "display_name": "Vacation Mode",
          "device_id": null,
          "area_id": null,
          "area_name": "",
          "labels": [],
          "label_map": {"ignore_unavailable": false}
        }
      ]
    }
  }
}
```

- `entries` is keyed by config entry ID and includes every loaded integration
  entry, keeping the same shape for one or multiple entries.
- `devices_count` counts mapped devices; `entities_count` counts both device-linked
  and orphaned entities. Empty mappings return empty arrays and zero counts.
- Entity areas/labels are their own registry assignments, not inherited device
  values. `label_map` contains every known label ID with an explicit boolean.
- Orphans with a missing parent retain the original `device_id`; they are still
  returned in `orphan_entities`.

For example, a Node-RED **Function** node can flatten the REST response into lists:

```javascript
const entries = Object.values(msg.payload.service_response.entries);
msg.devices = entries.flatMap(entry => entry.devices);
msg.entities = entries.flatMap(entry => [
    ...entry.devices.flatMap(device => device.entities),
    ...entry.orphan_entities
]);
return msg;
```

Multiple integration entries map the same Home Assistant registry, so choose one
entry (or deduplicate by device `id` / `entity_id`) when combining their lists.

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
        entity_id: sensor.sh_entity_status_unsuppressed_list
        above: 0
    action:
      - service: notify.mobile_app_my_phone
        data:
          message: >
            {{ states('sensor.sh_entity_status_unsuppressed_list') }} unavailable items need attention.
```

### Template: list unsuppressed items

```yaml
{% set devices = state_attr('sensor.sh_entity_status_unsuppressed_list', 'devices') or [] %}
{% set orphans = state_attr('sensor.sh_entity_status_unsuppressed_list', 'entities') or [] %}
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
