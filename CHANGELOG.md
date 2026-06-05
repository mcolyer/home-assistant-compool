# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Reconcile optimistic control state with the controller within a few seconds of a change. v0.4.3 removed the immediate (stale) re-poll but then relied on the periodic poll, which `async_set_updated_data` pushes ~30s out, so a wrong optimistic value (e.g. an unacknowledged write) could linger. The batch flush now schedules a single delayed reconcile poll (just past the controller's ~2.5s heartbeat cadence) that overwrites the optimistic state with the real heartbeat without snapping back.

## [0.4.3] - 2026-06-05

### Fixed
- Fix the UI snapping a switch back to its previous state right after a change (and the resulting aux toggle desync): the post-write reconcile poll read the controller's heartbeat before it had caught up, so the stale value overwrote the correct optimistic state. The batch flush no longer re-polls immediately; the optimistic value stands until the next scheduled poll, by which time the heartbeat reflects the change.

## [0.4.2] - 2026-06-05

### Fixed
- Fix aux switches (e.g. pool lights) silently failing to turn **off**: pycompool's `set_aux_equipment` guarded its toggle with a lagging heartbeat read that matched the "off" request and skipped the command, so the UI showed off optimistically then snapped back on at the next poll. The integration now tracks the last polled aux state and sends an unconditional `toggle_aux_equipment` only when the desired state differs.

### Changed
- Replace the per-field write debounce with a single batched write queue: optimistic changes accumulate and the whole batch is sent to the controller once per collect window, followed by one reconciling refresh

## [0.4.1] - 2026-06-04

### Fixed
- Fix rapid successive changes (temperature, heater mode, aux switches) getting lost or snapping back by serializing all controller access behind a bus lock, applying optimistic state updates, and removing the stale immediate re-poll after each write
- Coalesce rapid same-field writes (e.g. temperature slider drags) behind a short debounce so only the final value is sent to the controller instead of flooding the RS485 bus

## [0.4.0] - 2026-06-04

### Fixed
- Fix pool/spa heater mode selects and heat source sensors showing "unknown" by mapping pycompool's integer heat-source codes (0-3) to mode strings in the coordinator

## [0.3.0] - 2025-09-29

### Fixed
- Fix heater mode selection bug that prevented proper heater control

## [0.2.4] - 2025-09-12

### Changed
- Upgrade pycompool dependency to v0.2.3 for latest features and bug fixes

## [0.2.3] - 2025-01-12

### Changed
- Upgrade pycompool dependency to v0.2.2 for latest features and bug fixes

## [0.2.2] - 2025-01-11

### Changed
- Upgrade pycompool dependency to v0.2.1 for improved reliability and bug fixes

### Technical Details
- Updated pycompool from v0.1.2 to v0.2.1 with dependency management improvements
- All existing functionality remains the same with enhanced stability

## [0.2.1] - 2025-06-23

### Fixed
- Fix entity device name error that prevented proper device registration and entity organization

## [0.2.0] - 2025-06-23

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