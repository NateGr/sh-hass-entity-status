# SH Entity Status

A Home Assistant custom integration that monitors entity availability across your entire HA instance and exposes configurable **suppression** — so that "expected" unavailability (a device under maintenance, a sensor you don't care about) doesn't pollute your dashboards or trigger false alerts.

---

## What It Does

- Continuously polls all HA entities for `unavailable` state.
- Classifies each unavailable entity as **unsuppressed** (needs attention) or **suppressed** (deliberately ignored).
- Exposes 5 sensors so you can build automations, Lovelace cards, or notifications based on the real health of your devices.

### Suppression Model

Suppression is controlled by a configurable HA **label** (default: `ignore_unavailable`).

| Applied to | Effect |
|---|---|
| An **entity** | That entity is suppressed (even if its device is not) |
| A **device** | All unavailable entities on that device are suppressed |

The two tiers are evaluated in order: entity-level first, then device-level on whatever remains.

---

## Minimum HA Version

**2026.3.0**

---

## Installation

### Via HACS (recommended)
1. In HACS, go to **Integrations → Custom Repositories**.
2. Add `https://github.com/NateGr/sh-hass-entity-status` (type: Integration).
3. Install **SH Entity Status** and restart Home Assistant.

### Manual
1. Download or clone this repository.
2. Copy `custom_components/sh_entity_status/` into your HA config's `custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

After installation, go to **Settings → Devices & Services → Add Integration** and search for **SH Entity Status**.

| Field | Default | Description |
|---|---|---|
| Integration name | `SH Entity Status` | Display name for this entry |
| Ignore label name | `ignore_unavailable` | HA label slug that marks entities/devices to suppress |
| Refresh interval (minutes) | `60` | How often to rebuild the registry hierarchy. Must be >= 1. |
| Poll interval (seconds) | `30` | How often to check for unavailable entities. Must be >= 5. |

All options are editable post-setup via the **Configure** button on the integration card.

---

## Sensors

| Entity ID | State | Description |
|---|---|---|
| `sensor.unavailable_count` | integer | Total unavailable entities (suppressed + unsuppressed) |
| `sensor.unsuppressed_unavailable_count` | integer | Unavailable entities that need attention |
| `sensor.suppressed_count` | integer | Unavailable entities that are intentionally ignored |
| `sensor.unavailable_list` | integer (count) | Count + full device/entity details as attributes |
| `sensor.suppressed_list` | integer (count) | Count + full suppressed device/entity details as attributes |

### Attributes on `unavailable_list`

```yaml
unsuppressed_entities:
  - entity_id: light.living_room
    name: Living Room
    device_id: abc123
    area_id: living_room
    area_name: Living Room
    labels: []
    label_map: {}
unsuppressed_devices:
  - id: abc123
    name: Philips Hue Bulb
    area_name: Living Room
    labels: []
    entities: [...]
```

### Attributes on `suppressed_list`

Same structure with `suppressed_entities` and `suppressed_devices` keys.

---

## Services

| Service | Description |
|---|---|
| `sh_entity_status.refresh_registry` | Rebuild the in-memory device/entity/label hierarchy immediately |
| `sh_entity_status.poll_unavailable` | Immediately re-poll for unavailable entities |
| `sh_entity_status.reload` | Reload all SH Entity Status config entries |

---

## Using Suppression Labels

### Suppress a single entity
1. Open the entity in HA.
2. Go to **Settings** and add the label `ignore_unavailable` (or your custom label name).
3. The entity will appear in the suppressed list on the next poll.

### Suppress an entire device
1. Open the device in HA.
2. Go to **Settings** and add the label `ignore_unavailable`.
3. All unavailable entities on that device will be suppressed.

---

## Automation Example

```yaml
automation:
  - alias: Alert on new unavailable entities
    trigger:
      - platform: numeric_state
        entity_id: sensor.unsuppressed_unavailable_count
        above: 0
    action:
      - service: notify.mobile_app_my_phone
        data:
          message: >
            {{ states('sensor.unsuppressed_unavailable_count') }} entities are unavailable.
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

1. Fork the repository.
2. Install test dependencies: `pip install -r requirements_test.txt`
3. Run tests: `python -m pytest tests/ -v`
4. Submit a pull request against `main`.

Please ensure all tests pass and add tests for new behaviour.
