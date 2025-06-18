# Compool Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

A comprehensive Home Assistant integration for Compool pool controllers. Monitor your pool and spa temperatures, equipment status, and operational states with real-time sensor data and automation capabilities.

## ✨ Features

### 🌡️ **Comprehensive Temperature Monitoring**
- **Pool Water Temperature**: Real-time pool temperature monitoring
- **Spa Water Temperature**: Dedicated spa temperature tracking
- **Air Temperature**: Ambient air temperature sensing
- **Solar Temperatures**: Solar collector and spa solar temperature monitoring
- **Precise Readings**: Temperature readings in Fahrenheit with 1°F precision

### 🔧 **Equipment Status & Control**
- **Heat Source Monitoring**: Track active heating source (solar, heater, etc.)
- **System Status**: Monitor heat delay and freeze protection states
- **Fault Detection**: Sensor fault indicators for air, solar, and water sensors
- **Solar System**: Solar presence detection and status monitoring
- **Firmware Info**: Controller firmware version and time display

### 🏠 **Home Assistant Native**
- **Local Communication**: Direct RS485 over TCP connection (no cloud dependency)
- **Real-time Updates**: 30-second polling intervals for responsive monitoring
- **Config Flow Setup**: Easy IP/port configuration through the UI
- **Device Registry**: Proper device representation with metadata
- **Entity Naming**: Follows Home Assistant conventions with proper device classes
- **HACS Compatible**: Easy installation and updates

## 📦 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/mcolyer/home-assistant-compool` as an Integration
6. Search for "Compool" and install
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/compool` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration through the UI

## ⚙️ Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Compool"
4. Enter your pool controller connection details:
   - **Host**: IP address of your RS485 to TCP converter
   - **Port**: TCP port (default: 8899)

### Network Requirements
- **RS485 to TCP Converter**: Required to connect pool controller to network
- **Local Network Access**: Integration communicates directly with your pool controller
- **No Cloud Dependencies**: All communication is local to your network

## 📈 Sensors

The integration creates the following sensors for your pool controller:

### Temperature Sensors
| Sensor | Description | Unit | Device Class |
|--------|-------------|------|--------------|
| **Pool Water Temperature** | Current pool water temperature | °F | Temperature |
| **Spa Water Temperature** | Current spa water temperature | °F | Temperature |
| **Spa Solar Temperature** | Spa solar temperature | °F | Temperature |
| **Air Temperature** | Ambient air temperature | °F | Temperature |
| **Solar Collector Temperature** | Solar collector temperature | °F | Temperature |

### Status Sensors
| Sensor | Description | Device Class |
|--------|-------------|--------------|
| **Firmware** | Controller firmware version | - |
| **Controller Time** | Controller system time | Timestamp |
| **Active Heat Source** | Currently active heating source | - |

### Binary Sensors
| Sensor | Description | Device Class |
|--------|-------------|--------------|
| **Heat Delay Active** | Heat delay status indicator | - |
| **Freeze Protection Active** | Freeze protection status | - |
| **Air Sensor Fault** | Air sensor fault indicator | Problem |
| **Solar Sensor Fault** | Solar sensor fault indicator | Problem |
| **Water Sensor Fault** | Water sensor fault indicator | Problem |
| **Solar Present** | Solar system presence indicator | - |

## 🔧 Services

Currently, no additional services are implemented. All pool controller data is available through the sensor entities listed above. Future versions may include services for pool control functions.

## 🚀 Automation Examples

### Freeze Protection Alert
```yaml
automation:
  - alias: "Freeze Protection Activated"
    trigger:
      - platform: state
        entity_id: binary_sensor.compool_freeze_protection_active
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Pool freeze protection has been activated!"
          title: "🧊 Freeze Protection Alert"
```

### High Temperature Warning
```yaml
automation:
  - alias: "Pool Temperature Too High"
    trigger:
      - platform: numeric_state
        entity_id: sensor.compool_pool_water_temperature
        above: 90  # 90°F
    action:
      - service: notify.family
        data:
          message: "Pool temperature is {{ states('sensor.compool_pool_water_temperature') }}°F - consider reducing heat!"
```

### Sensor Fault Notification
```yaml
automation:
  - alias: "Pool Sensor Fault Alert"
    trigger:
      - platform: state
        entity_id: 
          - binary_sensor.compool_air_sensor_fault
          - binary_sensor.compool_solar_sensor_fault
          - binary_sensor.compool_water_sensor_fault
        to: "on"
    action:
      - service: notify.homeowner
        data:
          message: >
            Pool controller sensor fault detected: {{ trigger.to_state.attributes.friendly_name }}
          title: "⚠️ Pool Controller Alert"
```

### Daily Pool Report
```yaml
automation:
  - alias: "Daily Pool Status Report"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: notify.homeowner
        data:
          message: >
            Pool Status:
            🌡️ Pool: {{ states('sensor.compool_pool_water_temperature') }}°F
            🛁 Spa: {{ states('sensor.compool_spa_water_temperature') }}°F
            ☀️ Active Heat: {{ states('sensor.compool_pool_active_heat_source') }}
```

## 🔄 Data Updates

- **Status Data**: Updates every 30 seconds for real-time monitoring
- **Local Communication**: Direct TCP connection to pool controller
- **Brief Connections**: Connect, get status, disconnect pattern minimizes network overhead

The integration uses efficient local polling that provides real-time updates without overwhelming your network or pool controller.

## 🛠️ Development

### Requirements
- Python 3.13+
- Home Assistant 2025.6.0+
- pycompool v0.1.2 library

### Setup Development Environment
```bash
# Clone the repository
git clone https://github.com/mcolyer/home-assistant-compool.git
cd home-assistant-compool

# Install dependencies
scripts/setup

# Run tests
scripts/test

# Start development instance
scripts/develop
```

### Testing
The integration includes comprehensive test coverage:
- Unit tests for all components
- Integration tests with mocked pool controller responses
- Config flow testing for all scenarios
- Temperature sensor and binary sensor testing

Run tests with: `scripts/test`

## 📚 Documentation

- **[pycompool Library](https://pypi.org/project/pycompool/)**: Underlying pool controller communication library
- **[Home Assistant Developer Docs](https://developers.home-assistant.io/)**: Integration development guide
- **Compool Controllers**: Compatible with Compool pool automation systems

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `scripts/test`
6. Run linting: `scripts/lint`
7. Submit a pull request

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🐛 Issues & Support

- **Bug Reports**: [GitHub Issues](https://github.com/mcolyer/home-assistant-compool/issues)
- **Feature Requests**: [GitHub Issues](https://github.com/mcolyer/home-assistant-compool/issues)
- **Discussion**: [Home Assistant Community](https://community.home-assistant.io/)

## ⭐ Acknowledgments

- Powered by the [pycompool](https://pypi.org/project/pycompool/) library
- Inspired by the Home Assistant community's dedication to home automation

---

**Disclaimer**: This integration is not officially affiliated with Compool. Use at your own risk.

[releases-shield]: https://img.shields.io/github/release/mcolyer/home-assistant-compool.svg?style=for-the-badge
[releases]: https://github.com/mcolyer/home-assistant-compool/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/mcolyer/home-assistant-compool.svg?style=for-the-badge
[commits]: https://github.com/mcolyer/home-assistant-compool/commits/main
[license-shield]: https://img.shields.io/github/license/mcolyer/home-assistant-compool.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[user]: https://github.com/mcolyer
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40mcolyer-blue.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/mcolyer
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge