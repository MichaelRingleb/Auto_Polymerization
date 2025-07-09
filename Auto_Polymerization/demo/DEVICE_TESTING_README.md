# Device Testing Guide for Auto_Polymerization Platform

This guide explains how to test the real devices in your Auto_Polymerization platform using the provided test scripts.

## Overview

The device testing system consists of two main files:
- `device_test_controller.py` - Comprehensive testing framework
- `demo_device_test.py` - Simple demo script for quick testing

## Prerequisites

Before running device tests, ensure:

1. **Hardware is connected and powered on**
2. **Medusa design JSON file is available** (usually in `users/config/`)
3. **All required Python packages are installed**:
   - `medusa-sdl`
   - `matterlab_spectrometers`
   - `numpy`
   - `pathlib`

## Quick Start

### Option 1: Run the Demo (Recommended for first-time users)

```bash
cd demo
python demo_device_test.py
```

This will guide you through testing individual devices with safe parameters.

### Option 2: Use the Full Test Controller

```bash
cd demo
python device_test_controller.py
```

This provides a comprehensive menu-driven interface for all device testing.

## Device Types and Test Functions

### 1. Pumps

#### Syringe Pumps
- **Function**: `test_syringe_pump()`
- **Devices**: `Solvent_Monomer_Modification_Pump`, `Initiator_CTA_Pump`, `Analytical_Pump`, `Precipitation_Pump`
- **Test**: Transfers a small volume (default 1.0 mL) between vessels
- **Safety**: User confirmation required

#### Peristaltic Pumps
- **Function**: `test_peristaltic_pump()`
- **Devices**: `Polymer_Peri_Pump`, `Solvent_Peri_Pump`
- **Test**: Runs pump for a specified duration (default 10 seconds)
- **Safety**: User confirmation required

### 2. Valves

#### Gas Valve
- **Function**: `test_gas_valve()`
- **Control**: Serial commands `GAS_ON` and `GAS_OFF`
- **Test**: Opens and closes gas valve with delays
- **Safety**: User confirmation required

#### Solenoid Valve
- **Function**: `test_solenoid_valve()`
- **Control**: Serial commands `PRECIP_ON` and `PRECIP_OFF`
- **Test**: Opens and closes solenoid valve for precipitation
- **Safety**: User confirmation required

### 3. Linear Actuator
- **Function**: `test_linear_actuator()`
- **Control**: Serial commands with position values
- **Test**: Moves between positions 1000 (lower) and 2000 (upper)
- **Safety**: User confirmation required

### 4. Heating and Stirring
- **Function**: `test_heating_stirring()`
- **Device**: Hotplate for reaction vial
- **Test**: Heats to test temperature (25°C) and stirs at test RPM (100)
- **Monitoring**: Reads temperature for 30 seconds
- **Safety**: User confirmation required

### 5. UV-VIS Spectrometer
- **Function**: `test_uv_vis_spectrometer()`
- **Device**: CCS200 spectrometer
- **Test**: Takes a reference spectrum
- **Output**: Saves spectrum file and returns metadata
- **Safety**: User confirmation required

## Test Parameters

Default test parameters (can be modified in the controller):

```python
test_volume = 1.0  # mL for syringe pumps
test_temperature = 25  # °C for heating
test_rpm = 100  # RPM for stirring
test_transfer_rate = 0.5  # mL/min for peristaltic pumps
```

## Safety Features

### User Confirmations
All potentially dangerous operations require user confirmation:
- Pump operations
- Valve control
- Heating operations
- Actuator movements

### Error Handling
- Comprehensive try-catch blocks
- Detailed error logging
- Graceful failure handling
- Test result reporting

### Safe Defaults
- Small test volumes (1.0 mL)
- Moderate temperatures (25°C)
- Short test durations
- Conservative transfer rates

## Example Usage

### Testing a Single Device

```python
from demo.device_test_controller import DeviceTestController

# Initialize controller
controller = DeviceTestController("path/to/your/design.json")
controller.initialize_medusa()

# Test a syringe pump
result = controller.test_syringe_pump(
    pump_id="Solvent_Monomer_Modification_Pump",
    source="Solvent_Vessel",
    target="Waste_Vessel",
    volume=0.5
)

print(f"Test result: {result['success']}")
```

### Running All Tests

```python
# Run comprehensive test suite
results = controller.run_all_tests()
print(f"Tests passed: {results['successful_tests']}/{results['total_tests']}")
```

## Troubleshooting

### Common Issues

1. **Medusa Initialization Fails**
   - Check that the JSON design file path is correct
   - Ensure all required dependencies are installed
   - Verify hardware connections

2. **Pump Tests Fail**
   - Check vessel names in your design file
   - Ensure vessels contain sufficient liquid
   - Verify pump connections and power

3. **UV-VIS Tests Fail**
   - Check spectrometer USB connection
   - Ensure device ID is correct (M00479664)
   - Verify spectrometer is powered on

4. **Serial Communication Errors**
   - Check COM port settings
   - Ensure Arduino/controller is connected
   - Verify serial commands are correct
   - Run `python test_com_ports.py` to diagnose COM port issues

### Debug Mode

Enable detailed logging by modifying the logging level:

```python
logger.setLevel(logging.DEBUG)
```

### COM Port Troubleshooting

If you encounter Arduino initialization errors, run the diagnostic script:

```bash
cd demo
python test_com_ports.py
```

This script will:
1. List all available COM ports
2. Test direct Arduino connection
3. Test Medusa serial command functionality
4. Provide troubleshooting tips

**Common COM Port Issues:**
- **Wrong COM port**: The Arduino might be on a different COM port than COM12
- **Arduino not responding**: Check if the Arduino code is uploaded and running
- **Driver issues**: Ensure Arduino drivers are properly installed
- **USB cable**: Try a different USB cable or port

## File Structure

```
Auto_Polymerization/
├── demo/
│   ├── device_test_controller.py      # Main testing framework
│   ├── demo_device_test.py            # Demo script
│   ├── test_com_ports.py              # COM port diagnostic tool
│   ├── DEVICE_TESTING_README.md       # This file
│   └── test_uv_vis_utils.py           # UV-VIS testing utilities
├── platform_controller.py             # Original workflow controller
└── users/
    └── config/
        └── fluidic_design_autopoly.json  # Medusa design file
```

## Integration with Workflow

The test functions are designed to be compatible with your existing workflow modules. You can:

1. **Import test functions** into your workflow modules:
   ```python
   from demo.device_test_controller import DeviceTestController
   ```
2. **Use test results** to validate device states
3. **Integrate safety checks** into your main workflow
4. **Add custom test parameters** for specific experiments

## Best Practices

1. **Always run tests before experiments** to ensure devices are working
2. **Use small volumes** for initial testing
3. **Monitor device responses** during tests
4. **Keep test logs** for troubleshooting
5. **Update test parameters** based on your specific setup

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the test logs for error messages
3. Verify hardware connections and power
4. Ensure all dependencies are properly installed

## Version History

- **v1.0**: Initial release with comprehensive device testing framework
- Includes all major device types from the platform
- Safety features and user confirmations
- Demo script for easy testing 