"""Tests for the SH Entity Status coordinator unavailable model."""

from unittest.mock import MagicMock

from custom_components.sh_entity_status.coordinator import (
    SHEntityStatusCoordinator,
    _format_duration,
)
from datetime import timedelta


def _make_state(entity_id: str, state: str = "unavailable") -> MagicMock:
    state_obj = MagicMock()
    state_obj.entity_id = entity_id
    state_obj.state = state
    return state_obj


def _make_coordinator(
    states: list[MagicMock] | None = None,
    devices: dict[str, dict] | None = None,
    orphans: list[dict] | None = None,
) -> SHEntityStatusCoordinator:
    """Build a coordinator with mocked hass and pre-populated registry cache."""
    hass = MagicMock()
    hass.states.async_all.return_value = states or []

    coord = SHEntityStatusCoordinator.__new__(SHEntityStatusCoordinator)
    coord.hass = hass
    coord._ignore_label = "ignore_unavailable"
    coord._devices = devices or {}
    coord._orphan_entities = orphans or []
    coord._downtime_start = {}
    coord._last_downtime_duration = None
    return coord


def test_unsuppressed_device_and_orphan_counts() -> None:
    """Unsuppressed category includes devices and orphaned entities."""
    device_entity = {
        "entity_id": "sensor.temp",
        "name": "Temp",
        "device_id": "dev1",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    orphan_entity = {
        "entity_id": "input_boolean.helper_flag",
        "name": "Helper Flag",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {"ignore_unavailable": False},
    }
    device = {
        "id": "dev1",
        "name": "Climate Sensor",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {"ignore_unavailable": False},
        "entities": [device_entity],
    }

    coord = _make_coordinator(
        states=[_make_state("sensor.temp"), _make_state("input_boolean.helper_flag")],
        devices={"dev1": device},
        orphans=[orphan_entity],
    )

    device_without_entities = {k: v for k, v in device.items() if k != "entities"}

    result = coord._compute_unavailable()

    assert result["unsuppressed_unavailable_count"] == 2
    assert result["suppressed_unavailable_count"] == 0
    assert result["unsuppressed_unavailable_devices"] == [device_without_entities]
    assert result["suppressed_unavailable_devices"] == []
    assert result["unsuppressed_orphaned_unavailable_entities"] == [orphan_entity]
    assert result["suppressed_orphaned_unavailable_entities"] == []
    # Diagnostic fields
    assert result["total_devices_count"] == 1
    assert result["total_entities_count"] == 2  # 1 device entity + 1 orphan
    assert result["heartbeat"] == "active"


def test_suppressed_device_and_orphan_counts() -> None:
    """Suppressed category includes suppressed devices and orphaned entities."""
    device_entity = {
        "entity_id": "sensor.suppressed_temp",
        "name": "Suppressed Temp",
        "device_id": "dev_supp",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    orphan_entity = {
        "entity_id": "input_boolean.suppressed_helper",
        "name": "Suppressed Helper",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
    }
    suppressed_device = {
        "id": "dev_supp",
        "name": "Ignored Device",
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
        "entities": [device_entity],
    }

    coord = _make_coordinator(
        states=[
            _make_state("sensor.suppressed_temp"),
            _make_state("input_boolean.suppressed_helper"),
        ],
        devices={"dev_supp": suppressed_device},
        orphans=[orphan_entity],
    )

    suppressed_device_without_entities = {
        k: v for k, v in suppressed_device.items() if k != "entities"
    }

    result = coord._compute_unavailable()

    assert result["unsuppressed_unavailable_count"] == 0
    assert result["suppressed_unavailable_count"] == 2
    assert result["unsuppressed_unavailable_devices"] == []
    assert result["suppressed_unavailable_devices"] == [
        suppressed_device_without_entities
    ]
    assert result["unsuppressed_orphaned_unavailable_entities"] == []
    assert result["suppressed_orphaned_unavailable_entities"] == [orphan_entity]


def test_entity_with_missing_device_treated_as_orphaned_unsuppressed() -> None:
    """Entity with missing device should be handled as unsuppressed orphan by default."""
    missing_parent = {
        "entity_id": "sensor.legacy_node",
        "name": "Legacy Node",
        "device_id": "missing_dev",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {"ignore_unavailable": False},
    }
    coord = _make_coordinator(
        states=[_make_state("sensor.legacy_node")],
        orphans=[missing_parent],
    )

    result = coord._compute_unavailable()

    assert result["unsuppressed_unavailable_count"] == 1
    assert result["suppressed_unavailable_count"] == 0
    assert result["unsuppressed_orphaned_unavailable_entities"] == [missing_parent]


def test_unknown_unavailable_entity_defaults_to_unsuppressed_orphan() -> None:
    """Unavailable entities absent from cache should still be represented."""
    coord = _make_coordinator(states=[_make_state("sensor.unknown")])

    result = coord._compute_unavailable()

    assert result["unsuppressed_unavailable_count"] == 1
    assert result["suppressed_unavailable_count"] == 0
    assert result["unsuppressed_unavailable_devices"] == []
    assert result["suppressed_unavailable_devices"] == []
    assert (
        result["unsuppressed_orphaned_unavailable_entities"][0]["entity_id"]
        == "sensor.unknown"
    )
    assert result["suppressed_orphaned_unavailable_entities"] == []


def test_no_unavailable_entities() -> None:
    """Coordinator should return empty collections and zero counts."""
    coord = _make_coordinator(states=[])

    result = coord._compute_unavailable()

    assert result["unsuppressed_unavailable_count"] == 0
    assert result["suppressed_unavailable_count"] == 0
    assert result["unsuppressed_unavailable_devices"] == []
    assert result["suppressed_unavailable_devices"] == []
    assert result["unsuppressed_orphaned_unavailable_entities"] == []
    assert result["suppressed_orphaned_unavailable_entities"] == []
    assert result["total_devices_count"] == 0
    assert result["total_entities_count"] == 0
    assert result["recent_downtime_duration"] is None
    assert result["heartbeat"] == "active"


def test_downtime_tracking_records_recovery() -> None:
    """Downtime duration is recorded when an entity recovers."""
    coord = _make_coordinator(states=[_make_state("sensor.flaky")])

    # First poll — entity is unavailable; starts tracking
    coord._compute_unavailable()
    assert "sensor.flaky" in coord._downtime_start

    # Second poll — entity recovered
    coord.hass.states.async_all.return_value = []
    coord._compute_unavailable()

    assert coord._last_downtime_duration is not None
    assert "sensor.flaky" not in coord._downtime_start


def test_total_counts_reflect_registry() -> None:
    """total_devices_count and total_entities_count reflect the registry."""
    device = {
        "id": "dev1",
        "name": "A Device",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
        "entities": [
            {"entity_id": "sensor.a", "name": "A", "device_id": "dev1",
             "area_id": None, "area_name": "", "labels": [], "label_map": {}},
            {"entity_id": "sensor.b", "name": "B", "device_id": "dev1",
             "area_id": None, "area_name": "", "labels": [], "label_map": {}},
        ],
    }
    orphan = {
        "entity_id": "input_boolean.x",
        "name": "X",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    coord = _make_coordinator(devices={"dev1": device}, orphans=[orphan])

    result = coord._compute_unavailable()

    assert result["total_devices_count"] == 1
    assert result["total_entities_count"] == 3  # 2 device entities + 1 orphan


def test_format_duration_seconds() -> None:
    assert _format_duration(timedelta(seconds=45)) == "45s"


def test_format_duration_minutes() -> None:
    assert _format_duration(timedelta(minutes=3, seconds=20)) == "3m 20s"


def test_format_duration_hours() -> None:
    assert _format_duration(timedelta(hours=2, minutes=15)) == "2h 15m"
