"""Tests for SH Entity Status services."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sh_entity_status.const import DOMAIN
from custom_components.sh_entity_status.coordinator import SHEntityStatusCoordinator
from custom_components.sh_entity_status.services import (
    async_setup_services,
    async_unload_services,
)

ENTRY_DATA = {
    "ignore_label": "ignore_unavailable",
    "refresh_interval": 60,
    "poll_interval": 30,
}


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="svc_entry_id")


async def test_refresh_registry_service(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test that refresh_registry service triggers coordinator.async_refresh_registry."""
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

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    coordinator.async_refresh_registry = AsyncMock()

    await hass.services.async_call(DOMAIN, "refresh_registry", blocking=True)
    await hass.async_block_till_done()

    coordinator.async_refresh_registry.assert_called_once()


async def test_poll_unavailable_service(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test that poll_unavailable service triggers coordinator.async_request_refresh."""
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

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    coordinator.async_request_refresh = AsyncMock()

    await hass.services.async_call(DOMAIN, "poll_unavailable", blocking=True)
    await hass.async_block_till_done()

    coordinator.async_request_refresh.assert_called_once()


async def test_get_registry_service(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """The action returns the mapped registry, not just unavailable sensor data."""
    config_entry.add_to_hass(hass)
    area = ar.async_get(hass).async_create("Kitchen")
    label = lr.async_get(hass).async_create("ignore_unavailable")
    device_reg = dr.async_get(hass)
    device = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("test", "device")},
        name="Device",
    )
    device_reg.async_update_device(device.id, area_id=area.id, labels={label.label_id})
    entity_reg = er.async_get(hass)
    linked = entity_reg.async_get_or_create(
        "sensor", "test", "linked", device_id=device.id, original_name="Linked"
    )
    entity_reg.async_update_entity(
        linked.entity_id, area_id=area.id, labels={label.label_id}
    )
    disabled = entity_reg.async_get_or_create(
        "sensor",
        "test",
        "disabled",
        device_id=device.id,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    orphan = entity_reg.async_get_or_create(
        "input_boolean", "test", "helper", original_name="Helper"
    )
    hass.states.async_set(linked.entity_id, "on")
    hass.states.async_set(orphan.entity_id, "unavailable")
    coordinator = SHEntityStatusCoordinator(hass, config_entry)
    coordinator.async_request_refresh = AsyncMock()
    await coordinator.async_refresh_registry()
    hass.data[DOMAIN] = {config_entry.entry_id: coordinator, "other_data": {}}
    await async_setup_services(hass)
    states_before = hass.states.async_all()

    assert (
        hass.services.supports_response(DOMAIN, "get_registry") is SupportsResponse.ONLY
    )
    response = await hass.services.async_call(
        DOMAIN, "get_registry", {}, blocking=True, return_response=True
    )

    assert response["schema_version"] == 1
    assert list(response["entries"]) == [config_entry.entry_id]
    snapshot = response["entries"][config_entry.entry_id]
    assert snapshot["devices_count"] == 1
    assert snapshot["entities_count"] == 3
    assert snapshot["last_registry_refresh"] is not None
    exported_device = snapshot["devices"][0]
    assert exported_device["id"] == device.id
    assert exported_device["display_name"] == "Device (Kitchen)"
    assert exported_device["area_id"] == area.id
    assert exported_device["labels"] == [label.label_id]
    assert exported_device["label_map"] == {label.label_id: True}
    assert {entity["entity_id"] for entity in exported_device["entities"]} == {
        linked.entity_id,
        disabled.entity_id,
    }
    exported_linked = next(
        entity
        for entity in exported_device["entities"]
        if entity["entity_id"] == linked.entity_id
    )
    assert exported_linked["name"] == "Linked"
    assert exported_linked["display_name"] == "Linked (Kitchen)"
    assert exported_linked["device_id"] == device.id
    assert exported_linked["label_map"] == {label.label_id: True}
    assert snapshot["orphan_entities"][0]["entity_id"] == orphan.entity_id
    assert json.loads(json.dumps(response)) == response
    assert hass.states.async_all() == states_before
    coordinator.async_request_refresh.assert_awaited_once()


async def test_get_registry_multiple_entries(hass: HomeAssistant) -> None:
    """All loaded coordinators are exported independently under their entry IDs."""
    entries = [
        MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id=entry_id)
        for entry_id in ("first", "second")
    ]
    hass.data[DOMAIN] = {
        entry.entry_id: SHEntityStatusCoordinator(hass, entry) for entry in entries
    }
    await async_setup_services(hass)

    response = await hass.services.async_call(
        DOMAIN, "get_registry", blocking=True, return_response=True
    )

    assert set(response["entries"]) == {"first", "second"}
    assert all(snapshot["devices"] == [] for snapshot in response["entries"].values())
    assert all(
        snapshot["orphan_entities"] == [] for snapshot in response["entries"].values()
    )


async def test_get_registry_requires_response(hass: HomeAssistant) -> None:
    """Callers must explicitly request a response, and no fields are accepted."""
    await async_setup_services(hass)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, "get_registry", blocking=True)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "get_registry",
            {"unexpected": True},
            blocking=True,
            return_response=True,
        )


async def test_get_registry_empty_and_unload(hass: HomeAssistant) -> None:
    """Empty data is serializable and the response action is removed on unload."""
    await async_setup_services(hass)
    response = await hass.services.async_call(
        DOMAIN, "get_registry", blocking=True, return_response=True
    )
    assert response == {"schema_version": 1, "entries": {}}

    await async_unload_services(hass)
    assert not hass.services.has_service(DOMAIN, "get_registry")
