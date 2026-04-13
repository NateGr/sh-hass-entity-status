# Requirements Backlog

## Implemented (v1.0.0)

### Core Functionality
- **Registry hierarchy builder** — reads HA's entity, device, area, and label registries and builds an in-memory hierarchy (devices → entities, with area and label metadata).
- **Unavailability poll** — polls `hass.states` on a configurable interval (default 30 s) to find entities with `state == "unavailable"`.
- **Suppression logic (two-tier)**:
  - *Entity-level*: any unavailable entity that carries the configured ignore label is suppressed.
  - *Device-level*: after entity filtering, if the device carrying remaining unavailable entities itself has the ignore label, all those entities (and the device) are suppressed.
- **5 sensors**: `unavailable_count`, `unsuppressed_unavailable_count`, `suppressed_count`, `unavailable_list`, `suppressed_list`.
- **3 services**: `refresh_registry`, `poll_unavailable`, `reload`.
- **Config flow** (initial setup + options flow) with voluptuous validation.
- **Automatic registry re-refresh** on `entity_registry_updated` and `device_registry_updated` HA bus events.
- **Periodic registry refresh** timer (configurable, default 60 min).
- HACS-compatible packaging (`hacs.json`, `manifest.json`).
- Full pytest test suite (config flow, coordinator suppression logic, sensors, services).

---

## Backlog / Future Enhancements

### High Priority
- **Temporary / time-based suppression** — allow suppression to expire after N minutes/hours, e.g. to silence a device during maintenance without permanently labelling it.
- **Multiple ignore labels with ANY / ALL logic** — e.g. suppress if entity has *any* of a configured label set, or suppress only if it has *all* of them.

### Medium Priority
- **Dynamic label picker in config flow** — replace the free-text `ignore_label` field with a dropdown populated from HA's label registry at setup time.
- **Filter by area** — limit monitoring scope to specific areas only.
- **Filter by device class** — e.g. ignore motion sensors, or only watch climate entities.
- **Filter by entity type / platform** — e.g. only watch `sensor` and `binary_sensor` entities.

### Low Priority / Aspirational
- **Custom Lovelace card** — a dashboard card that visualises unavailable entities grouped by device and area, with suppression indicators.
- **Notification / persistent notification on change** — fire a HA notification when the unsuppressed count increases.
- **History / trending** — track how long entities have been unavailable.
- **MQTT / webhook push mode** — instead of polling, receive push events for state changes.
