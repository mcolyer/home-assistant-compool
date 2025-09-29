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
- **Platforms**: sensor, binary_sensor, number, select, switch
- **Communication**: Uses pycompool library (v0.2.3) for RS485 over TCP communication
- **Data Coordination**: CompoolStatusDataUpdateCoordinator handles local polling with 30-second intervals
- **Configuration**: Config entry-based setup with IP address and port (default 8899)

## Key Components

- `coordinator.py` - Data update coordinator for pool controller status polling
- `config_flow.py` - IP/port configuration flow with connection validation using get_status()
- `entity.py` - Base entity class for Compool pool controller entities
- `sensor.py` - Temperature and status sensors (firmware, time, temperatures, heat source)
- `binary_sensor.py` - Pool status binary sensors (heater_on, heat delay, freeze protection, sensor faults, solar presence)
- `number.py` - Target temperature controls for pool and spa
- `select.py` - Heater mode selection for pool and spa
- `switch.py` - Auxiliary equipment switches (8 aux circuits)
- `services.yaml` - Service definitions (set_pool_temperature, set_spa_temperature, set_heater_mode)

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

### Important API Data Structure Notes
- **Firmware Version**: pycompool returns `"version"` key (integer), not `"firmware"`
- **Heat Source Configuration**:
  - `heat_source`: Pool heat mode configuration (`'heater'`, `'solar-priority'`, `'solar-only'`, or `'off'`)
  - `spa_heat_source`: Spa heat mode configuration (`'heater'`, `'solar-priority'`, `'solar-only'`, or `'off'`)
  - These fields indicate the *configured* heating mode, not the current active state
- **Heater Active Status**:
  - `heater_on`: Boolean indicating whether the heater is *actively running* right now
  - This is separate from the configured heat mode
- **Temperature Keys**: Follow specific naming conventions (e.g., `air_temp_f`, `pool_solar_temp_f`, `spa_solar_temp` without _f suffix)
- **Time Format**: Returns as "HH:MM" string format, not ISO timestamp
- **Status Fields**: Include `heater_on`, `solar_on`, `freeze_protection_active`, sensor fault flags

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
- `sensor.pool_heat_source` - Pool heating mode configuration (heater/solar-priority/solar-only/off)
- `sensor.spa_heat_source` - Spa heating mode configuration (heater/solar-priority/solar-only/off)

**Binary Sensors:**
- `binary_sensor.heater_on` - Whether heater is actively running (separate from configured mode)
- `binary_sensor.heat_delay_active` - Heat delay status
- `binary_sensor.freeze_protection_active` - Freeze protection status
- `binary_sensor.air_sensor_fault` - Air sensor fault indicator
- `binary_sensor.solar_sensor_fault` - Solar sensor fault indicator
- `binary_sensor.water_sensor_fault` - Water sensor fault indicator
- `binary_sensor.solar_present` - Solar system presence indicator

**Number Entities:**
- `number.pool_target_temperature` - Pool target temperature (50-104°F)
- `number.spa_target_temperature` - Spa target temperature (50-104°F)

**Select Entities:**
- `select.pool_heater_mode` - Pool heater mode (off/heater/solar-priority/solar-only)
- `select.spa_heater_mode` - Spa heater mode (off/heater/solar-priority/solar-only)

**Switch Entities:**
- `switch.aux1` through `switch.aux8` - Auxiliary equipment controls

**Services:**
- `compool.set_pool_temperature` - Set pool target temperature
- `compool.set_spa_temperature` - Set spa target temperature
- `compool.set_heater_mode` - Set heater mode for pool or spa

## Development Environment

- **Python Version**: 3.13.2+ (required for Home Assistant 2025.6.0+)
- **Package Manager**: uv for dependency management
- **Development Container**: Available with Home Assistant pre-configured
- **Flox Environment**: Optional (`.flox/env/manifest.toml`) - scripts use `uv run` for environment isolation

## Testing

The integration includes a comprehensive test suite using pytest with Home Assistant custom component testing framework:

- `scripts/test` - Run full test suite
- `scripts/lint` - Run ruff linting and formatting
- Test files are in `tests/` directory with fixtures in `conftest.py`
- Tests use `MockConfigEntry` and bypass actual controller calls with `bypass_get_data` fixture
- Entity naming follows Home Assistant conventions (device_class determines entity IDs)

## Development Notes

- **Coordinator Sharing**: All platforms use the shared coordinator from `runtime_data`
- **Entity Naming**: Home Assistant generates entity IDs using device_class and translation keys
- **Polling Strategy**: Pool controller status updates every 30 seconds using brief TCP connections
- **Connection Pattern**: Connect briefly, get status, disconnect automatically to minimize connection overhead

## CI/CD & Code Quality

- **CI**: Runs lint, test, and hassfest validation on code changes (excludes docs)
- **Linting**: Ruff with Home Assistant specific rules - use `scripts/lint` to auto-fix
- **Testing**: pytest with Home Assistant custom component framework - mock pycompool in conftest.py
- **Coverage**: Codecov tracks test coverage
- **Important**: CI Python version (3.13.2) must match pyproject.toml `requires-python`

## Debugging Sensor Issues

- **"Unknown" Values**: Check const.py KEY_* constants match pycompool field names exactly
- **Field Name Quirks**:
  - pycompool uses `"version"` not `"firmware"` for firmware version
  - `heat_source`/`spa_heat_source` are configured modes (strings), `heater_on` is active status (boolean)
  - Temperature fields: inconsistent _f suffix (e.g., `air_temp_f` but `spa_solar_temp`)
  - Time format: "HH:MM" string, not ISO timestamp
- **Testing**: Use `uv run python -c "..."` for testing pycompool API directly

## Release Process

### Creating a Release
1. **Pre-release checklist**:
   - Run `scripts/test` to ensure all tests pass
   - Run `scripts/lint` to ensure code quality
   - Update `custom_components/compool/manifest.json` version field to match release version
   - Update CHANGELOG.md to move [Unreleased] section to new version with current date
   - Commit any pending changes (like uv.lock dependency updates, manifest, and CHANGELOG)
   
2. **Git tagging**:
   - Create semantic version tag: `git tag v0.1.0`
   - Push tag to remote: `git push origin v0.1.0`
   
3. **GitHub release**:
   - Use `gh release create v0.1.0 --title "v0.1.0 - Title" --notes "Release notes"`
   - Include comprehensive release notes with features, installation instructions, and requirements
   - Reference CHANGELOG.md for organized release content

### Release Notes Best Practices
- **Structure**: Use clear sections (Features, Installation, Requirements, etc.)
- **Feature Categories**: Group by sensor types (Temperature, Status, Binary sensors)
- **Installation Steps**: Include step-by-step setup instructions
- **Requirements**: Specify HA version, Python version, and dependencies
- **Technical Details**: Mention polling intervals, communication protocols, and integration features

### Dependency Management
- uv.lock updates are normal and should be committed before releases
- Dependency updates typically include: Home Assistant, ruff, pytest plugins, and other dev tools
- Always test after dependency updates to ensure compatibility