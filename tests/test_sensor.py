"""Tests for SH Entity Status sensor platform."""

from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sh_entity_status.const import DOMAIN


ENTRY_DATA = {
    "ignore_label": "ignore_unavailable",
    "refresh_interval": 60,
    "poll_interval": 30,
}


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="test_entry_id")


async def test_sensors_created(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test that all four sensors are created after setup."""
    config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator.async_setup"
        ),
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator._async_update_data",
            return_value={
                "unsuppressed_unavailable_count": 0,
                "suppressed_unavailable_count": 0,
                "unsuppressed_unavailable_devices": [],
                "suppressed_unavailable_devices": [],
                "unsuppressed_orphaned_unavailable_entities": [],
                "suppressed_orphaned_unavailable_entities": [],
            },
        ),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    expected_entity_ids = [
        "sensor.sh_entity_status_unsuppressed_unavailable_count",
        "sensor.sh_entity_status_suppressed_unavailable_count",
        "sensor.sh_entity_status_unsuppressed_unavailable_list",
        "sensor.sh_entity_status_suppressed_unavailable_list",
    ]
    for eid in expected_entity_ids:
        state = hass.states.get(eid)
        assert state is not None, f"Sensor {eid} not found in states"


async def test_sensor_unique_ids(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test that sensor unique_ids follow the expected pattern."""
    config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator.async_setup"
        ),
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator._async_update_data",
            return_value={
                "unsuppressed_unavailable_count": 0,
                "suppressed_unavailable_count": 0,
                "unsuppressed_unavailable_devices": [],
                "suppressed_unavailable_devices": [],
                "unsuppressed_orphaned_unavailable_entities": [],
                "suppressed_orphaned_unavailable_entities": [],
            },
        ),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    from homeassistant.helpers import entity_registry as er

    ent_reg = er.async_get(hass)
    sensor_keys = [
        "unsuppressed_unavailable_count",
        "suppressed_unavailable_count",
        "unsuppressed_unavailable_list",
        "suppressed_unavailable_list",
    ]
    for key in sensor_keys:
        expected_uid = f"{config_entry.entry_id}_{DOMAIN}_{key}"
        entry = ent_reg.async_get_entity_id("sensor", DOMAIN, expected_uid)
        assert entry is not None, (
            f"Unique ID {expected_uid} not found in entity registry"
        )


async def test_sensor_state_updates_with_coordinator_data(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test that sensor state reflects coordinator data."""
    config_entry.add_to_hass(hass)
    unsuppressed_device = {
        "id": "dev1",
        "name": "Unsuppressed Device",
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
        "entities": [],
    }
    suppressed_device = {
        "id": "dev2",
        "name": "Suppressed Device",
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
        "entities": [],
    }
    unsuppressed_orphan_entity = {
        "entity_id": "light.bedroom",
        "name": "Bedroom",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }
    suppressed_orphan_entity = {
        "entity_id": "light.ignore_me",
        "name": "Ignore Me",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": ["ignore_unavailable"],
        "label_map": {"ignore_unavailable": True},
    }

    with (
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator.async_setup"
        ),
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator._async_update_data",
            return_value={
                "unsuppressed_unavailable_count": 2,
                "suppressed_unavailable_count": 2,
                "unsuppressed_unavailable_devices": [unsuppressed_device],
                "suppressed_unavailable_devices": [suppressed_device],
                "unsuppressed_orphaned_unavailable_entities": [
                    unsuppressed_orphan_entity
                ],
                "suppressed_orphaned_unavailable_entities": [suppressed_orphan_entity],
            },
        ),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.sh_entity_status_unsuppressed_unavailable_count")
    assert state is not None
    assert state.state == "2"

    state = hass.states.get("sensor.sh_entity_status_suppressed_unavailable_count")
    assert state.state == "2"

    state = hass.states.get("sensor.sh_entity_status_unsuppressed_unavailable_list")
    assert state.state == "2"

    state = hass.states.get("sensor.sh_entity_status_suppressed_unavailable_list")
    assert state.state == "2"
