"""
Simple script to test COM port connectivity and diagnose Arduino issues.

This script helps identify if the Arduino is properly connected and responding
on COM12 before running the full device tests.

Usage:
    python test_com_ports.py
"""

import serial
import serial.tools.list_ports
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def list_available_ports():
    """List all available COM ports."""
    logger.info("Available COM ports:")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        logger.info(f"  {port.device}: {port.description}")
    return ports


def test_arduino_connection(com_port="COM12", baudrate=9600, timeout=2):
    """
    Test connection to Arduino on specified COM port.
    
    Args:
        com_port (str): COM port to test
        baudrate (int): Baud rate for communication
        timeout (int): Timeout in seconds
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    logger.info(f"Testing Arduino connection on {com_port}...")
    
    try:
        # Try to open the serial connection
        arduino = serial.Serial(com_port, baudrate, timeout=timeout)
        logger.info(f"Successfully opened {com_port}")
        
        # Wait for Arduino to reset
        time.sleep(2)
        
        # Test sending a simple command
        test_command = "1000\n"  # Move actuator to position 1000
        logger.info(f"Sending test command: {test_command.strip()}")
        arduino.write(test_command.encode())
        
        # Wait for response
        time.sleep(1)
        
        # Check if there's any response
        if arduino.in_waiting > 0:
            response = arduino.read(arduino.in_waiting).decode().strip()
            logger.info(f"Received response: {response}")
        else:
            logger.warning("No response received from Arduino")
        
        # Close the connection
        arduino.close()
        logger.info("Arduino connection test completed successfully")
        return True
        
    except serial.SerialException as e:
        logger.error(f"Serial connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def test_medusa_serial_commands():
    """Test if medusa can send serial commands."""
    try:
        from medusa import Medusa
        import logging
        
        # Setup medusa logger
        medusa_logger = logging.getLogger("medusa_test")
        medusa_logger.setLevel(logging.INFO)
        
        # Try to initialize medusa with the layout file
        from pathlib import Path
        layout_path = Path("../users/config/fluidic_design_autopoly.json")
        logger.info(f"Testing Medusa initialization with layout: {layout_path}")
        
        medusa = Medusa(
            graph_layout=layout_path,
            logger=medusa_logger
        )
        
        logger.info("Medusa initialized successfully")
        
        # Test sending a serial command
        logger.info("Testing serial command: GAS_ON")
        medusa.write_serial("COM12", "GAS_ON")
        time.sleep(1)
        
        logger.info("Testing serial command: GAS_OFF")
        medusa.write_serial("COM12", "GAS_OFF")
        
        logger.info("Medusa serial command test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Medusa test failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("COM Port and Arduino Connection Test")
    print("=" * 60)
    
    # List available ports
    print("\n1. Listing available COM ports:")
    ports = list_available_ports()
    
    if not ports:
        print("No COM ports found!")
        return
    
    # Test Arduino connection
    print("\n2. Testing Arduino connection:")
    arduino_success = test_arduino_connection()
    
    # Test Medusa serial commands
    print("\n3. Testing Medusa serial commands:")
    medusa_success = test_medusa_serial_commands()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Available COM ports: {len(ports)}")
    print(f"Arduino connection: {'✓ PASS' if arduino_success else '✗ FAIL'}")
    print(f"Medusa serial commands: {'✓ PASS' if medusa_success else '✗ FAIL'}")
    
    if arduino_success and medusa_success:
        print("\n🎉 All tests passed! Your Arduino should be working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
        print("\nTroubleshooting tips:")
        print("1. Make sure Arduino is connected and powered on")
        print("2. Check that the correct COM port is being used")
        print("3. Verify the Arduino code is uploaded and running")
        print("4. Check USB cable and drivers")


if __name__ == "__main__":
    main() 