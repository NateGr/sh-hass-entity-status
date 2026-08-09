"""Tests for the SmartHass Entity Status config flow."""

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.sh_entity_status.const import DOMAIN


async def test_user_flow_success(hass):
    """Test a successful user-initiated config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "title": "Test Integration",
            "ignore_label": "ignore_unavailable",
            "refresh_interval": 60,
            "poll_interval": 30,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Integration"
    assert result["data"]["ignore_label"] == "ignore_unavailable"
    assert result["data"]["refresh_interval"] == 60
    assert result["data"]["poll_interval"] == 30


async def test_user_flow_already_configured(hass):
    """Test that a second setup attempt is aborted (single-instance enforcement)."""
    # First setup succeeds
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "title": "First Entry",
            "ignore_label": "ignore_unavailable",
            "refresh_interval": 60,
            "poll_interval": 30,
        },
    )

    # Second setup attempt should abort
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_user_flow_invalid_refresh_interval(hass):
    """Test that refresh_interval < 1 raises InvalidData from HA schema validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "title": "Test",
                "ignore_label": "ignore_unavailable",
                "refresh_interval": 0,
                "poll_interval": 30,
            },
        )


async def test_user_flow_invalid_poll_interval(hass):
    """Test that poll_interval < 5 raises InvalidData from HA schema validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "title": "Test",
                "ignore_label": "ignore_unavailable",
                "refresh_interval": 60,
                "poll_interval": 4,
            },
        )


async def test_options_flow_updates_config(hass, mock_config_entry):
    """Test that the options flow updates configuration correctly."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "title": "Updated",
            "ignore_label": "new_label",
            "refresh_interval": 120,
            "poll_interval": 60,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options["ignore_label"] == "new_label"
    assert mock_config_entry.options["refresh_interval"] == 120
    assert mock_config_entry.options["poll_interval"] == 60
