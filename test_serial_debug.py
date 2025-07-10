import medusa
import json
import time
import serial
import serial.tools.list_ports

# Test the Arduino communication directly
def test_arduino_direct():
    """Test direct Arduino communication to see if COM12 is working"""
    print("Testing direct Arduino communication...")
    
    # List available ports
    ports = list(serial.tools.list_ports.comports())
    print("Available COM ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")
    
    # Try to connect to COM12 directly
    try:
        print("\nTrying direct connection to COM12...")
        arduino = serial.Serial("COM12", 9600, timeout=2)
        time.sleep(2)  # Give Arduino time to reset
        
        # Test a simple command
        test_command = "STATUS\n"
        print(f"Sending: {test_command.strip()}")
        arduino.write(test_command.encode())
        
        # Try to read response
        response = arduino.readline().decode().strip()
        print(f"Response: {response}")
        
        arduino.close()
        return True
    except Exception as e:
        print(f"Direct connection failed: {e}")
        return False

# Test with a minimal Medusa setup
def test_medusa_serial():
    """Test write_serial through Medusa"""
    print("\nTesting Medusa write_serial...")
    
    # Create a minimal JSON layout with just a serial device
    minimal_layout = {
        "nodes": [
            {
                "id": "COM12",
                "type": "SerialDevice",
                "properties": {
                    "port": "COM12",
                    "baudrate": 9600,
                    "timeout": 1
                }
            }
        ],
        "edges": []
    }
    
    # Save to temporary file
    with open("temp_layout.json", "w") as f:
        json.dump(minimal_layout, f)
    
    try:
        # Initialize Medusa
        medusa_instance = medusa.Medusa("temp_layout.json")
        
        # Test write_serial
        print("Testing write_serial with 'STATUS' command...")
        medusa_instance.write_serial("COM12", "STATUS")
        print("write_serial completed without exception")
        
        return True
    except Exception as e:
        print(f"Medusa write_serial failed: {e}")
        return False
    finally:
        # Clean up
        import os
        if os.path.exists("temp_layout.json"):
            os.remove("temp_layout.json")

if __name__ == "__main__":
    print("=== Serial Communication Debug Test ===\n")
    
    # Test 1: Direct Arduino communication
    direct_success = test_arduino_direct()
    
    # Test 2: Medusa write_serial
    medusa_success = test_medusa_serial()
    
    print(f"\n=== Results ===")
    print(f"Direct Arduino communication: {'✓' if direct_success else '✗'}")
    print(f"Medusa write_serial: {'✓' if medusa_success else '✗'}")
    
    if not direct_success:
        print("\nRecommendations:")
        print("1. Check if Arduino is connected to COM12")
        print("2. Verify Arduino IDE shows COM12 as the port")
        print("3. Try uploading the Arduino code again")
        print("4. Check if any other software is using COM12")
    
    if not medusa_success and direct_success:
        print("\nThe issue is in Medusa's write_serial implementation, not the Arduino.") 