
import serial
import serial.tools.list_ports
import time

# Search for a port whose description contains "Arduino"

# Define a function to move the actuator with a given PWM value (1000-2000), 1000 is fully retracted, 2000 is fully extended (10 cm)
def move_actuator(com_port, pwm_value):
    """
    arduino_port = None
    for port in serial.tools.list_ports.comports():
        if "Arduino" in port.description:
            arduino_port = port.device
            print(f"Found Arduino at: {arduino_port}")
            break
    """
    # If port is found, open the serial connection
    arduino = serial.Serial(com_port, 9600, timeout=1)
    time.sleep(2)  # Give Arduino time to reset
    if 1000 <= pwm_value <= 2000:
        command = f"{pwm_value}\n"
        arduino.write(command.encode())
        print(f"Sent: {command.strip()}")
    else:
        print("PWM value out of valid range (1000-2000).")
    arduino.close() # Close the connection after sending the command

def set_valve(com_port, relay_position):
    arduino = serial.Serial(com_port, 9600, timeout=1)
    time.sleep(2)  # Give Arduino time to reset
    command = f"{relay_position}\n"
    arduino.write(command.encode())
    print(f"Sent: {command.strip()}")
    arduino.close()  # Close the connection after sending the command)


if __name__ == "__main__":
    move_actuator("COM7",2000)  # Example usage with a PWM value of 1500 (half range), change com port accordingly to that of the arduino
    """for n in range(10):
        for pwm in range(1000, 2001,500 ):  # Example usage with PWM values from 1000 to 2000
            move_actuator(pwm)
            time.sleep(8)"""