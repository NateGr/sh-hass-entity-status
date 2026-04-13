# Requirements Backlog

## Implemented (v1.0.2)

### Core Functionality
- **Registry hierarchy builder** — reads HA entity/device/area/label registries and builds an in-memory hierarchy (`_devices` + `_orphan_entities`).
- **Unavailability poll** — polls `hass.states` on a configurable interval (default 30 s) and classifies `state == "unavailable"` items.
- **Suppression logic (current model)**:
  - Items are categorized into **unsuppressed** and **suppressed** groups.
  - Categories include both unavailable **devices** and unavailable **orphaned entities**.
  - Internally, device-linked and orphaned items remain split.
- **4 sensors**:
  - `sensor.sh_entity_status_unsuppressed_unavailable_count`
  - `sensor.sh_entity_status_suppressed_unavailable_count`
  - `sensor.sh_entity_status_unsuppressed_unavailable_list`
  - `sensor.sh_entity_status_suppressed_unavailable_list`
- **1 button**: `button.sh_entity_status_refresh_registry` (forces immediate registry rebuild and refresh).
- **3 services**: `refresh_registry`, `poll_unavailable`, `reload` (with `services.yaml` metadata).
- **Single integration device view** — entities are grouped under one virtual device via `DeviceInfo`.
- **Config flow** (initial setup + options flow) with voluptuous validation.
- **Automatic registry refresh hooks**:
  - Entity registry updated
  - Device registry updated
  - Label registry updated
- **Periodic registry refresh** timer (configurable, default 60 min).
- HACS-compatible packaging (`hacs.json`, `manifest.json`) and integration icon.
- Full pytest test suite (config flow, coordinator, sensors, button, services).

## Next Candidates

- Add optional include/exclude filtering for monitored areas.
- Add UI-facing diagnostics sensor attributes (last refresh time, poll duration).
- Add a dedicated diagnostics endpoint payload for easier troubleshooting exports.

---

## Backlog / Future Enhancements

### High Priority
- **Temporary / time-based suppression** — allow suppression to expire after N minutes/hours, e.g. to silence a device during maintenance without permanently labelling it.
- **Multiple ignore labels with ANY / ALL logic** — e.g. suppress if entity has *any* of a configured label set, or suppress only if it has *all* of them.
- **Verbose unavailable hierarchy service/API** — add a service or API endpoint that returns the full unavailable hierarchy (devices with child entities, orphaned entities, and suppression status) for external automation tools like Node-RED.
- **Auto-reload by label** — support reloading integrations/devices/entities that carry a configurable label (e.g. `auto_reload`), including options flow settings to enable/disable the feature, configure the label name and how long to wait before reloading the device (incase it is a temporary offline).

### Medium Priority
- **Dynamic label picker in config flow** — replace the free-text `ignore_label` field with a dropdown populated from HA's label registry at setup time.
- **Filter by area** — limit monitoring scope to specific areas only.
- **Filter by domain / platform** — e.g. only watch `sensor` and `binary_sensor` entities.
- **Expose last registry refresh timestamp** in a diagnostic entity attribute.

### Low Priority / Aspirational
- **Custom Lovelace card** — dashboard card that visualizes suppressed vs unsuppressed unavailable items.
- **Notification / persistent notification on change** — fire a HA notification when the unsuppressed count increases.
- **History / trending** — track how long entities have been unavailable.
- **MQTT / webhook push mode** — instead of polling, receive push events for state changes.
