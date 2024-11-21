# Internet Health Monitor for Home Assistant

A Home Assistant custom component that provides comprehensive internet connectivity monitoring and automatic recovery capabilities for remote or unmanned locations. This integration continuously monitors your internet connection through multiple methods and can automatically recover from outages by power cycling your modem/router when necessary.

## 🌟 Motivation & Background

This component was created to solve a specific challenge: managing internet connectivity at an unmanned remote location with a fiber connection that occasionally requires a modem reboot to restore service. Without on-site personnel, even simple connectivity issues could result in extended downtime.

The solution needed to:
- Reliably detect actual internet outages (not just local network issues)
- Attempt recovery automatically without human intervention
- Prevent excessive reboot cycles
- Provide detailed monitoring and notifications
- Be robust enough for unmanned operation

## ⚠️ Important Disclaimers

- **Network Equipment Safety**: This component includes functionality to automatically power cycle network equipment. Please ensure:
  - The switch entity you configure has proper access controls
  - You thoroughly test the power cycling automation with your specific setup
  - You understand the implications of automated power cycling on your network equipment
  - Your modem/router is compatible with power cycling operations
  - The power switch controlling your modem is reliable and properly configured

- **Not Official**: This is a community-created custom component, not an official Home Assistant integration
- **No Warranty**: This software is provided "as is", without warranty of any kind
- **Use at Own Risk**: Automated power cycling of network equipment could potentially cause issues with your ISP or equipment
- **Testing Recommended**: Always test the monitoring features before enabling automatic recovery

## 🔍 Features

### Comprehensive Health Checks
- **Multi-Provider DNS Resolution Testing**:
  - Google (8.8.8.8)
  - Cloudflare (1.1.1.1)
  - Quad9 (9.9.9.9)
  - OpenDNS (208.67.222.222)
  
- **TCP Connectivity Verification**:
  - Tests ports 80 and 443
  - Checks multiple major services:
    - Google
    - Amazon
    - Cloudflare
    - GitHub
    - Microsoft

- **HTTP Connectivity Testing**:
  - Attempts connections to multiple major websites
  - Verifies actual data transfer
  - Validates HTTP response codes

### Smart Recovery System
- **Confidence Scoring**:
  - Weighted evaluation of all checks:
    - TCP checks: 45% weight
    - HTTP checks: 35% weight
    - DNS checks: 20% weight
  - Requires 60% confidence threshold for "healthy" status

- **Safety Mechanisms**:
  - Maximum 3 recovery attempts within 2 hours
  - Required cool-down period between attempts
  - Multiple validation checks before power cycling
  - Post-recovery validation
  - Automatic attempt counter reset after successful recovery

### Monitoring & Notifications
- Detailed status reporting
- Comprehensive logging
- Configurable notifications
- Historical tracking of recovery attempts

## 📦 Installation

### HACS Installation (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed
2. Add this repository to HACS:
   - Open HACS in Home Assistant
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add URL: `https://github.com/stoffee/hass-internet-health`
   - Category: Integration
3. Click "Download"
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/internet_health` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## ⚙️ Configuration

### 1. Basic Setup

Add to your `configuration.yaml`:

```yaml
# Required entities for tracking recovery attempts
input_number:
  internet_reboot_attempts:
    name: Internet Reboot Attempts
    min: 0
    max: 10
    step: 1
    mode: box

input_datetime:
  last_internet_reboot:
    name: Last Internet Reboot Time
    has_date: true
    has_time: true

# Your modem power switch configuration
switch:
  - platform: template  # Or your actual switch platform
    switches:
      internet_power:
        friendly_name: "Internet Modem Power"
        # Configure based on your actual modem power control method
```

### 2. Auto-Recovery Automation

Create this automation either in your `automations.yaml` or through the UI:

```yaml
alias: Internet Health Monitor - Auto Recovery
description: Monitors internet health and attempts recovery by power cycling modem.
trigger:
  - platform: time_pattern
    minutes: /5
  - platform: state
    entity_id: sensor.internet_health
    to: offline
condition:
  - condition: or
    conditions:
      - condition: template
        value_template: >
          {% set attempts = states('input_number.internet_reboot_attempts')|int(0) %}
          {% if attempts < 3 %}true{% else %}
          {% set last_reboot = states('input_datetime.last_internet_reboot') %}
          {% set hours_since = (as_timestamp(now()) - as_timestamp(last_reboot)) / 3600 %}
          {{ hours_since > 2 }}{% endif %}
action:
  # See full automation example in repository
```

## 🔒 Safety Features Explained

### 1. Accurate Problem Detection
- Multiple check types prevent false positives
- Weighted scoring system ensures accurate status
- Requires multiple services to be unreachable before triggering
- Built-in validation delays between checks

### 2. Recovery Attempt Limits
- Maximum 3 attempts within 2 hours
- Required 2-hour cooldown after reaching limit
- Automatic reset of attempt counter after successful recovery
- Configurable attempt limits and cooldown periods

### 3. Power Cycle Protection
- 30-second delay after power off before power on
- Verification of power state changes
- Post-recovery validation period
- Monitoring of recovery success rate

### 4. Notification System
- Detailed status notifications
- Recovery attempt notifications
- Success/failure reporting
- Historical tracking

## 📊 Monitoring

The component creates several entities:

- `sensor.internet_health`: Main status sensor
  - States: online/offline
  - Attributes: 
    - Confidence score
    - Check results
    - Failed check details
    - Last check timestamp

- `input_number.internet_reboot_attempts`: Recovery attempt counter
- `input_datetime.last_internet_reboot`: Timestamp of last recovery

## 🔧 Troubleshooting

### Common Issues

1. False Positives
   - Check firewall rules
   - Verify DNS server accessibility
   - Review TCP port accessibility

2. Recovery Not Working
   - Verify switch entity control
   - Check power cycle timing
   - Review automation logs

3. Excessive Attempts
   - Verify cooldown configuration
   - Check attempt counter functionality
   - Review notification history

### Debug Logging

Enable detailed logging:

```yaml
logger:
  default: info
  logs:
    custom_components.internet_health: debug
```

## 📝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.