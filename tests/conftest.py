"""Pytest configuration and shared fixtures."""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sh_entity_status.const import DOMAIN


# Enable custom integrations for all tests in this package
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically enable custom integrations for all tests."""
    return


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "title": "SH Entity Status",
            "ignore_label": "ignore_unavailable",
            "refresh_interval": 60,
            "poll_interval": 30,
        },
    )
