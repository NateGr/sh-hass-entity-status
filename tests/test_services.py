"""Tests for SH Entity Status services."""

from unittest.mock import AsyncMock, patch

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
