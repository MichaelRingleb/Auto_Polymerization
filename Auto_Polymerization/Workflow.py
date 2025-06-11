import sys
import os
import time
import serial
import serial.tools.list_ports


base_dir = os.path.dirname(__file__)
pumps_src = os.path.abspath(os.path.join(base_dir, "source", "Pumps", "src"))                   #add Pumps source directory 
serial_dev_src = os.path.abspath(os.path.join(base_dir, "source", "SerialDevice", "src"))       #add SerialDevice source directory  
actuator_src = os.path.abspath(os.path.join(base_dir, "source", "LinearActuator","src")) #add LinearActuator source directory to sys.path
hotplate_src = os.path.abspath(os.path.join(base_dir, "source", "Hotplates", "src")) #add Hotplate source directory to sys.path
sys.path.append(pumps_src)
sys.path.append(serial_dev_src)
sys.path.append(actuator_src)
sys.path.append(hotplate_src)


from matterlab_pumps.longer_peri import LongerPeristalticPump
from matterlab_serial_device.serial_device import SerialDevice, open_close
from matterlab_hotplates.ika_hotplate import IKAHotplate
from linear_actuator import move_actuator


# Function to convert string input to boolean
def str_to_bool(s):
    return s.strip().lower() in ("true", "1", "yes", "y")

def test_peristaltic_pump(com_port, rpm_in, direct_in, on_in):
    # Test control of Peristaltic pump
    while True:

        pump_solvent = LongerPeristalticPump(com_port="COM10", address=1)
        rpm_in= input("pump_solvent rpm:")
        direct_in = input("pump_solvent direction (True/False):")
        on_in=input("pump_solvent on/off (True/False):")
        pump_solvent.set_pump(on=str_to_bool(on_in), 
              direction=str_to_bool(direct_in), 
              rpm=float(rpm_in)) # Example to set pump on, CCW direction, and 100 RPM
        print(pump_solvent.query_pump())
    

        pump_polymer = LongerPeristalticPump(com_port="COM12", address=2)
        rpm_in= input("pump_polymer rpm:")
        direct_in = input("pump_polymer direction (True/False):")
        on_in=input("pump_polymer on/off (True/False):")
        pump_polymer.set_pump(on=str_to_bool(on_in), 
              direction=str_to_bool(direct_in), 
              rpm=float(rpm_in)) # Example to set pump on, CCW direction, and 100 RPM
        print(pump_polymer.query_pump())
    

def test_relay(com_port, relay_pos):
    for port in serial.tools.list_ports.comports():
         if "Arduino" in port.description:
            arduino_port = port.device
            print(f"Found Arduino at: {arduino_port}")
            break
    arduino = serial.Serial(arduino_port, 9600, timeout=1)
    time.sleep(2)
    if relay_pos == "ON":
        arduino.write(b"ON\n")
    else:
        arduino.write(b"OFF\n")
    arduino.close()



def test_actuator(com_port, actuator_pos):
    # Test control of linear actuator
    # Move actuator to certain position (1000 = 0%, 2000 = 100%)
    while True:
        actuator_pos = int(input("actuator position (1000 - 2000):"))
        move_actuator(actuator_pos) # Move actuator to half position

def test_hotplate(com_port, _temp, _rpm, heat_switch):
    #Test control of IKA hotplate
    hotplate = IKAHotplate(com_port="COM7", max_temp=200, max_rpm=1700) 
    hotplate.temp = _temp  # Set hotplate temperature
    hotplate.rpm = _rpm  # Set hotplate RPM
    time.sleep(5)  # Wait for 5 seconds to allow hotplate to stabilize
    hotplate._heat_switch = heat_switch   # Turn off heating
    print(hotplate.query_hotplate())  # Query hotplate status




"""
# Test control of continous syringe pump
from serial import Serial
dev = Serial("COM11", timeout = 1)
dev.write(b"\x71\x00")
"""

if __name__ == "__main__":
    


   test_actuator("COM5", 1000)
   
   #test_relay("COM5", "OFF")