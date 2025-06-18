# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- `scripts/setup` - Install Python dependencies and dev dependencies using uv
- `scripts/develop` - Start Home Assistant in debug mode with this custom component
- `scripts/lint` - Format and lint code using ruff
- `scripts/test` - Run pytest test suite

## Architecture

This is a Home Assistant custom component for Compool pool controllers. The integration is built on the integration_blueprint template structure:

- **Domain**: `compool` (defined in const.py and manifest.json)
- **Platforms**: Binary sensor and sensor platforms
- **Communication**: Uses pycompool library for RS485 over TCP communication
- **Data Coordination**: CompoolStatusDataUpdateCoordinator handles local polling with 30-second intervals
- **Configuration**: Config entry-based setup with IP address and port (default 8899)

## Key Components

- `coordinator.py` - Data update coordinator for pool controller status polling
- `config_flow.py` - IP/port configuration flow with connection validation using get_status()
- `entity.py` - Base entity class for Compool pool controller entities
- `sensor.py` - Temperature and status sensors (firmware, time, temperatures, heat source)
- `binary_sensor.py` - Pool status binary sensors (heat delay, freeze protection, sensor faults, solar presence)
- `services.yaml` - Service definitions (currently none implemented)

## Data Model

Compool integration works with:
- **Pool Controller**: Single RS485-connected device accessible over TCP
- **Status Data**: Real-time pool controller status including temperatures, operational states, and fault conditions
- **Connection**: Direct TCP connection to RS485 interface, brief connections for data retrieval

## PyCompool API Coverage

The integration utilizes pycompool APIs:

### Core APIs
- ✅ `PoolController(device, baud_rate)` - Creates controller instance with TCP device string
- ✅ `get_status()` - Used for connection validation and data polling
- ✅ Connection management - Automatic connect/disconnect for each status query

### Available Sensors

**Temperature Sensors:**
- `sensor.pool_water_temperature` - Pool water temperature in °F
- `sensor.spa_water_temperature` - Spa water temperature in °F
- `sensor.spa_solar_temperature` - Spa solar temperature in °F  
- `sensor.pool_air_temperature` - Air temperature in °F
- `sensor.solar_collector_temperature` - Solar collector temperature in °F

**Status Sensors:**
- `sensor.pool_controller_firmware` - Controller firmware version
- `sensor.pool_controller_time` - Controller timestamp
- `sensor.pool_active_heat_source` - Currently active heating source

**Binary Sensors:**
- `binary_sensor.heat_delay_active` - Heat delay status
- `binary_sensor.freeze_protection_active` - Freeze protection status
- `binary_sensor.air_sensor_fault` - Air sensor fault indicator
- `binary_sensor.solar_sensor_fault` - Solar sensor fault indicator
- `binary_sensor.water_sensor_fault` - Water sensor fault indicator
- `binary_sensor.solar_present` - Solar system presence indicator

## Development Environment

The integration includes a development container setup with Home Assistant pre-configured. The `config/configuration.yaml` enables debug logging for the custom component. The PYTHONPATH is modified during development to include the custom_components directory.

## Testing

The integration includes a comprehensive test suite using pytest with Home Assistant custom component testing framework:

- `scripts/test` - Run full test suite
- `scripts/lint` - Run ruff linting and formatting
- Test files are in `tests/` directory with fixtures in `conftest.py`
- Tests use `MockConfigEntry` and bypass actual controller calls with `bypass_get_data` fixture
- Entity naming follows Home Assistant conventions (device_class determines entity IDs)

## Development Notes

- **Coordinator Sharing**: Both sensor and binary_sensor platforms use the shared coordinator from `runtime_data` instead of creating new instances
- **Entity Naming**: Home Assistant generates entity IDs using device_class and translation keys
- **Manifest Requirements**: HA 2025.6.0+ requires a "version" field in manifest.json  
- **Python Version**: Uses Python 3.13.3 managed by uv for compatibility with latest HA versions
- **Polling Strategy**: Pool controller status updates every 30 seconds using brief TCP connections for real-time monitoring
- **Local Communication**: Uses pycompool v0.1.2 for RS485 over TCP communication with pool controllers
- **Connection Pattern**: Connect briefly, get status, disconnect automatically to minimize connection overhead