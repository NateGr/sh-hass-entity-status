"""Tests for SH Entity Status sensor platform."""
import pytest
from unittest.mock import MagicMock, patch

from homeassistant.const import STATE_UNKNOWN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sh_entity_status.const import DOMAIN


ENTRY_DATA = {
    "ignore_label": "ignore_unavailable",
    "refresh_interval": 60,
    "poll_interval": 30,
}


@pytest.fixture
def config_entry():
    return MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="test_entry_id")


async def test_sensors_created(hass, config_entry):
    """Test that all 5 sensors are created after setup."""
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator.async_setup"
    ), patch(
        "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator._async_update_data",
        return_value={
            "unsuppressed_entities": [],
            "suppressed_entities": [],
            "unsuppressed_devices": [],
            "suppressed_devices": [],
        },
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    expected_entity_ids = [
        "sensor.unavailable_count",
        "sensor.unsuppressed_unavailable_count",
        "sensor.suppressed_count",
        "sensor.unavailable_list",
        "sensor.suppressed_list",
    ]
    for eid in expected_entity_ids:
        state = hass.states.get(eid)
        assert state is not None, f"Sensor {eid} not found in states"


async def test_sensor_unique_ids(hass, config_entry):
    """Test that sensor unique_ids follow the expected pattern."""
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator.async_setup"
    ), patch(
        "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator._async_update_data",
        return_value={
            "unsuppressed_entities": [],
            "suppressed_entities": [],
            "unsuppressed_devices": [],
            "suppressed_devices": [],
        },
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    from homeassistant.helpers import entity_registry as er
    ent_reg = er.async_get(hass)
    sensor_keys = [
        "unavailable_count",
        "unsuppressed_unavailable_count",
        "suppressed_count",
        "unavailable_list",
        "suppressed_list",
    ]
    for key in sensor_keys:
        expected_uid = f"{config_entry.entry_id}_{DOMAIN}_{key}"
        entry = ent_reg.async_get_entity_id("sensor", DOMAIN, expected_uid)
        assert entry is not None, f"Unique ID {expected_uid} not found in entity registry"


async def test_sensor_state_updates_with_coordinator_data(hass, config_entry):
    """Test that sensor state reflects coordinator data."""
    config_entry.add_to_hass(hass)

    mock_entity = {
        "entity_id": "light.bedroom",
        "name": "Bedroom",
        "device_id": None,
        "area_id": None,
        "area_name": "",
        "labels": [],
        "label_map": {},
    }

    with patch(
        "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator.async_setup"
    ), patch(
        "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator._async_update_data",
        return_value={
            "unsuppressed_entities": [mock_entity],
            "suppressed_entities": [],
            "unsuppressed_devices": [],
            "suppressed_devices": [],
        },
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.unavailable_count")
    assert state is not None
    assert state.state == "1"

    state = hass.states.get("sensor.unsuppressed_unavailable_count")
    assert state.state == "1"

    state = hass.states.get("sensor.suppressed_count")
    assert state.state == "0"
