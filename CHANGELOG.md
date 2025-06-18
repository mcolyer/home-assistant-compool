# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Fix entity naming issue where entities appeared as "pool_controller_none" by adding proper English translations
- Entities now display with descriptive names like "Pool Water Temperature", "Heat Delay Active", etc.
- Fix Pool Controller Firmware sensor showing "Unknown" by using correct 'version' key from pycompool API
- Fix Pool Controller Active Heat Source sensor by computing value from heater_on/solar_on status
- Update temperature sensor key mappings to match pycompool library format

### Added
- English translation file (`translations/en.json`) for proper entity naming
- Computed field logic in coordinator for deriving active heat source from system status
- Enhanced status data processing to handle pycompool API differences
- Comprehensive sensor debugging documentation in CLAUDE.md

### Technical Details
- Updated const.py sensor key mappings to match pycompool API field names
- Added _enhance_status_data() method in coordinator to compute derived sensor values
- Updated test mock data to reflect actual pycompool response structure

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