# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Pool Temperature Control** - Three new services for controlling pool and spa temperatures
  - `compool.set_pool_temperature` - Set pool target temperature with numeric value + unit (°F/°C)
  - `compool.set_spa_temperature` - Set spa target temperature with numeric value + unit (°F/°C)
  - `compool.set_heater_mode` - Set heater mode (off/heater/solar-priority/solar-only) for pool or spa
- **Number Entities** - Temperature control sliders for pool and spa target temperatures (50-104°F range)
- **Select Entities** - Dropdown controls for pool and spa heater mode selection
- **Service Validation** - Unit-aware temperature validation (50-104°F or 10-40°C based on unit parameter)
- **UI Integration** - Multiple access methods: Developer Tools, dashboard service cards, number sliders, select dropdowns

### Fixed
- Fix entity naming issue where entities appeared as "pool_controller_none" by adding proper English translations
- Entities now display with descriptive names like "Pool Water Temperature", "Heat Delay Active", etc.
- Fix Pool Controller Firmware sensor showing "Unknown" by using correct 'version' key from pycompool API
- Fix Pool Controller Active Heat Source sensor by computing value from heater_on/solar_on status
- Update temperature sensor key mappings to match pycompool library format

### Technical Details
- Added comprehensive pool control functionality using pycompool API (`set_pool_temperature`, `set_spa_temperature`, `set_heater_mode`)
- Implemented shared coordinator backend for all control methods with proper error handling
- Created service schemas with custom validation for temperature ranges based on unit
- Added number and select platforms with proper entity configuration
- Enhanced test suite with 22/22 tests passing including comprehensive service and entity coverage
- Updated const.py sensor key mappings to match pycompool API field names
- Added _enhance_status_data() method in coordinator to compute derived sensor values
- Updated test mock data to reflect actual pycompool response structure
- Simplified release workflow to create integration ZIP for easy installation

## [0.1.0] - Initial Release

### Added
- Initial integration for Compool pool controllers
- Connection configuration via IP address and port (default 8899)
- Temperature sensors for pool water, spa water, air, and solar collector
- Binary sensors for heat delay, freeze protection, and sensor faults
- Status sensors for firmware version, controller time, and active heat source
- Data coordinator with 30-second polling interval
- Comprehensive test suite with pytest
- Development environment setup with Home Assistant integration
- CI/CD pipeline with GitHub Actions
- Code quality tools (Ruff linting and formatting)

### Technical Details
- Built on Home Assistant integration blueprint template
- Uses pycompool library for RS485 over TCP communication
- Config entry-based setup with connection validation
- Proper device registry integration
- Entity naming follows Home Assistant conventions