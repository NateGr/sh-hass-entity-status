# Developer Specification — SmartHass Entity Status

## Development Environment Setup

### Prerequisites
- Python 3.12+
- A Home Assistant development environment (or just the test dependencies for unit testing)

### Install test dependencies

```bash
pip install -r requirements_test.txt
```

### Run the test suite

```bash
python -m pytest tests/ -v
```

All tests should pass. The suite covers:
- Config flow (success path, invalid interval validation)
- Coordinator logic (device + orphaned entity categorization)
- Sensor creation, unique IDs, and state updates
- Button entity creation and press behavior
- Services (`refresh_registry`, `poll_unavailable`)

---

## Installing in Home Assistant for Development

### Manual installation
1. Copy the `custom_components/sh_entity_status/` directory into your HA config's `custom_components/` folder.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **SmartHass Entity Status**.

### HACS installation
1. Add this repository as a custom HACS repository (type: Integration).
2. Install **SmartHass Entity Status** via HACS.
3. Restart HA and add the integration via the UI.

---

## Code Structure

```
custom_components/sh_entity_status/
├── __init__.py        Entry points: async_setup_entry, async_unload_entry, async_reload_entry
├── const.py           All constants (domain slug, config keys, defaults)
├── config_flow.py     ConfigFlow + OptionsFlow with voluptuous schema
├── coordinator.py     SHEntityStatusCoordinator — registry + poll logic
├── sensor.py          4 CoordinatorEntity sensors
├── button.py          Refresh Registry button entity
├── services.py        3 HA services
├── services.yaml      HA service metadata (name + description)
├── manifest.json      Integration manifest
├── strings.json       UI strings (source of truth)
└── translations/
    └── en.json        English translations (mirrors strings.json)
```

---

## Key Design Decisions

### Single domain constant
`DOMAIN` is defined **only** in `const.py`. Every other file imports it from there. To rename the domain:
1. Change `DOMAIN` in `const.py`.
2. Rename the `custom_components/sh_entity_status/` directory to match.
3. Update `manifest.json` `domain` and `hacs.json` `filename`.
4. Rename the `translations/` files if needed.

### Coordinator pattern
The integration uses HA's `DataUpdateCoordinator` for the polling loop. The coordinator also holds the in-memory registry hierarchy (`_devices`, `_orphan_entities`). These are rebuilt independently from the poll cycle — on a longer timer (default 60 min) plus on registry change events.

### Categorization is stateless
Suppression/categorization is computed fresh on every poll. There is no persistent suppression state. This keeps the logic simple and deterministic.

### Device page grouping
All entities share the same `DeviceInfo.identifiers` tuple `(DOMAIN, entry.entry_id)`, which makes Home Assistant show one integration device page containing the sensors and button.

---

## Extensibility Points

| What to extend | Where to change |
|---|---|
| Add a new filter criterion (e.g. area, domain) | `coordinator.py` → `_compute_unavailable()` |
| Add a new sensor metric | `sensor.py` → `_SENSOR_DESCRIPTIONS` + `native_value` |
| Add a new button action | `button.py` |
| Add a new service | `services.py` → `async_setup_services()` |
| Document service in UI | `services.yaml` |
| Change ignore label logic (multiple labels, ANY/ALL) | `coordinator.py` → `_compute_unavailable()` |
| Add time-based suppression | `coordinator.py` — store suppression timestamps, check in `_compute_unavailable()` |
| Dynamic label picker in config flow | `config_flow.py` — query `lr.async_get(hass).labels` and build a `SelectSelector` |

---

## Testing Strategy

Coordinator suppression logic is unit-tested with pure Python (no HA fixtures needed) by directly instantiating `SHEntityStatusCoordinator.__new__` and injecting mock registries and states. This makes the tests fast and resilient to HA version changes.

Config flow, sensor, and service tests use the `hass` fixture from `pytest-homeassistant-custom-component`. Custom integrations must be explicitly enabled via the `enable_custom_integrations` fixture — this is wired up as an `autouse` fixture in `tests/conftest.py`.

---

## Linting / CI

Current CI includes:
- `ruff` linting in `.github/workflows/ci.yml`
- `pytest` execution in `.github/workflows/ci.yml`

Clean CI dependency verification for linting:
- CI explicitly installs `ruff` (`python -m pip install ruff`)
- CI verifies availability on a fresh runner (`python -m ruff --version`)
- Lint then runs with `python -m ruff check .`

Recommended future additions:
- `mypy` for type checking (HA-style strict config)
