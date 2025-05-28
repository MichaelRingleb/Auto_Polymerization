import serial
import serial.tools.list_ports
import time

# Search for a port whose description contains "Arduino"
arduino_port = None
for port in serial.tools.list_ports.comports():
    if "Arduino" in port.description:
        arduino_port = port.device
        print(f"Found Arduino at: {arduino_port}")
        break

if arduino_port is None:
    raise Exception("No Arduino device found. Please check the connection.")

# If port is found, open the serial connection
arduino = serial.Serial(arduino_port, 9600, timeout=1)
time.sleep(2)  # Give Arduino time to reset

def move_actuator(pwm_value):
    if 1000 <= pwm_value <= 2000:
        command = f"{pwm_value}\n"
        arduino.write(command.encode())
        print(f"Sent: {command.strip()}")
    else:
        print("PWM value out of valid range (1000-2000).")

# Optional: close the connection
# arduino.close()


if __name__ == "__main__":
    move_actuator(1000)  # Example usage with a PWM value of 1500 (half range)
    """for n in range(10):
        for pwm in range(1000, 2001,500 ):  # Example usage with PWM values from 1000 to 2000
            move_actuator(pwm)
            time.sleep(8)"""