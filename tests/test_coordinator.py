"""Tests for the SH Entity Status coordinator suppression logic."""

import pytest
from unittest.mock import MagicMock, patch

from custom_components.sh_entity_status.coordinator import SHEntityStatusCoordinator
from custom_components.sh_entity_status.const import DOMAIN


def _make_state(entity_id: str, state: str = "unavailable"):
    s = MagicMock()
    s.entity_id = entity_id
    s.state = state
    return s


def _make_coordinator(
    ignore_label="ignore_unavailable", states=None, devices=None, orphans=None
):
    """Build a coordinator with mocked hass and pre-populated in-memory registry."""
    hass = MagicMock()
    hass.states.async_all.return_value = states or []

    config_entry = MagicMock()
    config_entry.data = {
        "ignore_label": ignore_label,
        "refresh_interval": 60,
        "poll_interval": 30,
    }
    config_entry.options = {}

    coord = SHEntityStatusCoordinator.__new__(SHEntityStatusCoordinator)
    coord.hass = hass
    coord._ignore_label = ignore_label
    coord._devices = devices or {}
    coord._orphan_entities = orphans or []
    return coord


# ---------------------------------------------------------------------------
# Scenario 1: Entity with ignore label → suppressed
# ---------------------------------------------------------------------------


def test_entity_with_ignore_label_suppressed():
    entity = {
        "entity_id": "light.kitchen",
        "name": "Kitchen",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
    }
    coord = _make_coordinator(
        states=[_make_state("light.kitchen")],
        orphans=[entity],
    )
    result = coord._compute_unavailable()
    assert result["suppressed_entities"] == [entity]
    assert result["unsuppressed_entities"] == []


# ---------------------------------------------------------------------------
# Scenario 2: Entity without ignore label → unsuppressed
# ---------------------------------------------------------------------------


def test_entity_without_ignore_label_unsuppressed():
    entity = {
        "entity_id": "light.living_room",
        "name": "Living Room",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    coord = _make_coordinator(
        states=[_make_state("light.living_room")],
        orphans=[entity],
    )
    result = coord._compute_unavailable()
    assert result["unsuppressed_entities"] == [entity]
    assert result["suppressed_entities"] == []


# ---------------------------------------------------------------------------
# Scenario 3: Device with ignore label → all its entities suppressed
# ---------------------------------------------------------------------------


def test_device_with_ignore_label_suppresses_all_entities():
    entity1 = {
        "entity_id": "sensor.temp",
        "name": "Temp",
        "device_id": "dev1",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    entity2 = {
        "entity_id": "sensor.humidity",
        "name": "Humidity",
        "device_id": "dev1",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    device = {
        "id": "dev1",
        "name": "Climate Sensor",
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
        "entities": [entity1, entity2],
    }
    coord = _make_coordinator(
        states=[_make_state("sensor.temp"), _make_state("sensor.humidity")],
        devices={"dev1": device},
    )
    result = coord._compute_unavailable()
    assert len(result["suppressed_entities"]) == 2
    assert result["unsuppressed_entities"] == []
    assert device in result["suppressed_devices"]
    assert result["unsuppressed_devices"] == []


# ---------------------------------------------------------------------------
# Scenario 4: Device without ignore label but entity has label → entity suppressed,
#             device still unsuppressed because other entities are unavailable
# ---------------------------------------------------------------------------


def test_device_without_ignore_label_entity_suppressed_device_unsuppressed():
    entity_labelled = {
        "entity_id": "sensor.labelled",
        "name": "Labelled",
        "device_id": "dev2",
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
    }
    entity_normal = {
        "entity_id": "sensor.normal",
        "name": "Normal",
        "device_id": "dev2",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    device = {
        "id": "dev2",
        "name": "Mixed Device",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
        "entities": [entity_labelled, entity_normal],
    }
    coord = _make_coordinator(
        states=[_make_state("sensor.labelled"), _make_state("sensor.normal")],
        devices={"dev2": device},
    )
    result = coord._compute_unavailable()
    assert entity_labelled in result["suppressed_entities"]
    assert entity_normal in result["unsuppressed_entities"]
    assert device in result["unsuppressed_devices"]
    assert result["suppressed_devices"] == []


# ---------------------------------------------------------------------------
# Scenario 5: Mixed scenario — multiple devices
# ---------------------------------------------------------------------------


def test_mixed_scenario():
    ent_suppressed_entity_level = {
        "entity_id": "light.ignore_me",
        "name": "Ignore Me",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
    }
    ent_device_suppressed = {
        "entity_id": "sensor.device_ignored",
        "name": "Device Ignored",
        "device_id": "dev_ignored",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    ent_normal = {
        "entity_id": "binary_sensor.door",
        "name": "Door",
        "device_id": "dev_normal",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    device_ignored = {
        "id": "dev_ignored",
        "name": "Ignored Device",
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
        "entities": [ent_device_suppressed],
    }
    device_normal = {
        "id": "dev_normal",
        "name": "Normal Device",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
        "entities": [ent_normal],
    }
    coord = _make_coordinator(
        states=[
            _make_state("light.ignore_me"),
            _make_state("sensor.device_ignored"),
            _make_state("binary_sensor.door"),
        ],
        devices={"dev_ignored": device_ignored, "dev_normal": device_normal},
        orphans=[ent_suppressed_entity_level],
    )
    result = coord._compute_unavailable()
    assert ent_suppressed_entity_level in result["suppressed_entities"]
    assert ent_device_suppressed in result["suppressed_entities"]
    assert ent_normal in result["unsuppressed_entities"]
    assert device_ignored in result["suppressed_devices"]
    assert device_normal in result["unsuppressed_devices"]


# ---------------------------------------------------------------------------
# Scenario 6: No unavailable entities
# ---------------------------------------------------------------------------


def test_no_unavailable_entities():
    coord = _make_coordinator(states=[])
    result = coord._compute_unavailable()
    assert result == {
        "unsuppressed_entities": [],
        "suppressed_entities": [],
        "unsuppressed_devices": [],
        "suppressed_devices": [],
    }


# ---------------------------------------------------------------------------
# Scenario 7: label_map contains the ignore label with value False → NOT suppressed
# (guards the full true/false label_map format introduced after the label registry fix)
# ---------------------------------------------------------------------------


def test_entity_with_label_false_not_suppressed():
    """An entity whose label_map has ignore_label=False must NOT be suppressed."""
    entity = {
        "entity_id": "light.bedroom",
        "name": "Bedroom",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {"ignore_unavailable": False},
    }
    coord = _make_coordinator(
        states=[_make_state("light.bedroom")],
        orphans=[entity],
    )
    result = coord._compute_unavailable()
    assert result["unsuppressed_entities"] == [entity]
    assert result["suppressed_entities"] == []


def test_device_with_label_false_not_suppressed():
    """A device whose label_map has ignore_label=False must NOT suppress its entities."""
    entity = {
        "entity_id": "sensor.motion",
        "name": "Motion",
        "device_id": "dev3",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {"ignore_unavailable": False},
    }
    device = {
        "id": "dev3",
        "name": "Motion Sensor",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {"ignore_unavailable": False},
        "entities": [entity],
    }
    coord = _make_coordinator(
        states=[_make_state("sensor.motion")],
        devices={"dev3": device},
    )
    result = coord._compute_unavailable()
    assert result["unsuppressed_entities"] == [entity]
    assert device in result["unsuppressed_devices"]
    assert result["suppressed_entities"] == []
    assert result["suppressed_devices"] == []
