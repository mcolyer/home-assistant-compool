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

    # Create a mock PoolController class with all needed methods
    mock_controller = MagicMock()
    mock_controller.get_status.return_value = MOCK_POOL_STATUS
    mock_controller.set_pool_temperature.return_value = True
    mock_controller.set_spa_temperature.return_value = True
    mock_controller.set_heater_mode.return_value = True
    mock_controller.set_aux_equipment.return_value = True

    with patch(
        "custom_components.compool.coordinator.PoolController",
        return_value=mock_controller,
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
