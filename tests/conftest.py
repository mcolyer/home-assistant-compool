"""Global fixtures for Compool integration tests."""

# Mock pycompool module at the module level
import sys
from unittest.mock import MagicMock, patch

import pytest

from .const import MOCK_POOL_STATUS

sys.modules["pycompool"] = MagicMock()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    return


@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with (
        patch("homeassistant.components.persistent_notification.async_create"),
        patch("homeassistant.components.persistent_notification.async_dismiss"),
    ):
        yield


@pytest.fixture(name="bypass_get_data")
def bypass_get_data_fixture():
    """Skip calls to get data from pool controller."""

    with (
        patch(
            "custom_components.compool.coordinator.PoolController.get_status",
            return_value=MOCK_POOL_STATUS,
        ),
    ):
        yield


@pytest.fixture(name="error_on_connect")
def error_on_connect_fixture():
    """Simulate error when connecting to pool controller."""
    with patch(
        "custom_components.compool.coordinator.CompoolStatusDataUpdateCoordinator._get_pool_status_with_retry",
        side_effect=Exception("Connection failed"),
    ):
        yield
