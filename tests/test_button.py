"""Tests for SH Entity Status button platform."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sh_entity_status.const import DOMAIN


ENTRY_DATA = {
    "ignore_label": "ignore_unavailable",
    "refresh_interval": 60,
    "poll_interval": 30,
}

MOCK_COORDINATOR_DATA = {
    "unsuppressed_unavailable_count": 0,
    "suppressed_unavailable_count": 0,
    "unsuppressed_unavailable_devices": [],
    "suppressed_unavailable_devices": [],
    "unsuppressed_orphaned_unavailable_entities": [],
    "suppressed_orphaned_unavailable_entities": [],
}


async def test_refresh_registry_button_created(
    hass: HomeAssistant,
) -> None:
    """Test that the Refresh Registry button entity is created after setup."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="btn_entry_id")
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator.async_setup"
        ),
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator._async_update_data",
            return_value=MOCK_COORDINATOR_DATA,
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("button.sh_entity_status_refresh_registry")
    assert state is not None


async def test_refresh_registry_button_press_calls_refresh(
    hass: HomeAssistant,
) -> None:
    """Test that pressing the button calls coordinator.async_refresh_registry."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="btn_entry_id2")
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator.async_setup"
        ),
        patch(
            "custom_components.sh_entity_status.coordinator.SHEntityStatusCoordinator._async_update_data",
            return_value=MOCK_COORDINATOR_DATA,
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_refresh_registry = AsyncMock()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.sh_entity_status_refresh_registry"},
        blocking=True,
    )
    await hass.async_block_till_done()

    coordinator.async_refresh_registry.assert_called_once()
