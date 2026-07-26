"""Pytest configuration and shared fixtures."""
import sys

import pytest
import pytest_socket
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sh_entity_status.const import DOMAIN

if sys.platform.startswith("win"):
    _orig_disable_socket = pytest_socket.disable_socket

    def _disable_socket_windows_passthrough(*args, **kwargs):
        return None

    pytest_socket.disable_socket = _disable_socket_windows_passthrough


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup() -> None:
    """Re-enable sockets on Windows for local pytest/asyncio compatibility."""
    if sys.platform.startswith("win"):
        pytest_socket.enable_socket()


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
