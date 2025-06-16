import sys
import os
import time
import serial
import serial.tools.list_ports

# Add the source directories to sys.path
base_dir = os.path.dirname(__file__)
pumps_src = os.path.abspath(os.path.join(base_dir, "source", "Pumps", "src"))                   #add Pumps source directory 
serial_dev_src = os.path.abspath(os.path.join(base_dir, "source", "SerialDevice", "src"))       #add SerialDevice source directory  
actuator_src = os.path.abspath(os.path.join(base_dir, "source", "LinearActuator","src")) #add LinearActuator source directory to sys.path
hotplate_src = os.path.abspath(os.path.join(base_dir, "source", "Hotplates", "src")) #add Hotplate source directory to sys.path
spectrometer_src = os.path.abspath(os.path.join(base_dir, "source", "Spectrometers", "src"))
sys.path.append(pumps_src)
sys.path.append(serial_dev_src)
sys.path.append(actuator_src)
sys.path.append(hotplate_src)
sys.path.append(spectrometer_src)

# Import necessary classes from the modules
from matterlab_pumps.longer_peri import LongerPeristalticPump
from matterlab_serial_device.serial_device import SerialDevice, open_close
from matterlab_hotplates.ika_hotplate import IKAHotplate
from linear_actuator import move_actuator
from matterlab_spectrometers.ccs_spectrometer import CCSSpectrometer

# Function to convert string input to boolean
def str_to_bool(s):
    return s.strip().lower() in ("true", "1", "yes", "y")


# Function to test the peristaltic pump
def test_peristaltic_pump(com_port, rpm_in, direct_in, on_in):
    while True:    
        # Test control of peristaltic pump for the solvent, address referes to the address of the pump on the DIP (see manual from Longer and also DIP panel on the pump)
        pump_solvent = LongerPeristalticPump(com_port="COM10", address=1)
        rpm_in= input("pump_solvent rpm:")                              #revolutions per minute on the pump (from 0.1 to 99)
        direct_in = input("pump_solvent direction (True/False):")       #True = clockwise, False = counter-clockwise
        on_in=input("pump_solvent on/off (True/False):")                #True = on, False = off

        pump_solvent.set_pump(on=str_to_bool(on_in), 
              direction=str_to_bool(direct_in), 
              rpm=float(rpm_in)) # Example to set pump on, CCW direction, and 100 RPM
        print(pump_solvent.query_pump())
        
        # Test control of peristaltic pump for the polymer, address referes to the address of the pump on the DIP (see manual from Longer and also DIP panel on the pump)
        pump_polymer = LongerPeristalticPump(com_port="COM12", address=2)
        rpm_in= input("pump_polymer rpm:")                          #revolutions per minute on the pump (from 0.1 to 99)
        direct_in = input("pump_polymer direction (True/False):")   #True = clockwise, False = counter-clockwise
        on_in=input("pump_polymer on/off (True/False):")            #True = on, False = off

        pump_polymer.set_pump(on=str_to_bool(on_in), 
              direction=str_to_bool(direct_in), 
              rpm=float(rpm_in)) # Example to set pump on, CCW direction, and 100 RPM
        print(pump_polymer.query_pump())
    

# Function to test the relay
def test_relay(com_port, relay_pos):
      
    arduino = serial.Serial(com_port, 9600, timeout=1)      #Open the serial port for communication
    time.sleep(2)                                           #Give Arduino time to reset
  
    if relay_pos == "ON" or relay_pos == "on":              #Turn on the relay -- this will close the normally open (NO) port at the solenoid valve
        arduino.write(b"ON\n")                              #Send command to turn on the relay to Arduino
    elif relay_pos == "OFF" or relay_pos == "off":          #Turn off the relay -- this will open the normally open (NO) port at the solenoid valve
        arduino.write(b"OFF\n")                             #Send command to turn off the relay to Arduino 
    arduino.close()                                         #Close the serial connection after sending the command


# Function to test the linear actuator, moves the actuator to a specified position (1000 = 0%, 2000 = 100% == 10 cm))
def test_actuator(com_port):
    while True:
        actuator_pos = int(input("actuator position (1000 - 2000):"))
        move_actuator(com_port, actuator_pos) 


# Function to test the IKA hotplate
def test_hotplate(com_port, _temp, _rpm, heat_switch):
    hotplate = IKAHotplate(com_port="COM7", max_temp=200, max_rpm=1700) #Initialize the hotplate with the specified COM port, max temperature, and max RPM
    hotplate.temp = _temp                                               #Set hotplate temperature
    hotplate.rpm = _rpm                                                 #Set hotplate RPM
    time.sleep(5)                                                       #Wait for 5 seconds to allow hotplate to stabilize
    hotplate._heat_switch = heat_switch                                 #Turn off heating
    #print(hotplate.query_hotplate())                                   #Query hotplate status


def test_ccs_spectrometer():
    spec = CCSSpectrometer(
        usb_port="USB",
        device_model="CCS200",
        device_id="M00479664"
    )
    spectrum = spec.measure_spectrum(0.1)  # 0.1 Sekunden Integrationszeit
    print("Spektrum:", spectrum)
    spec.close_instrument()
    


"""
# Test control of continous syringe pump
from serial import Serial
dev = Serial("COM11", timeout = 1)
dev.write(b"\x71\x00")
"""

if __name__ == "__main__":
   test_ccs_spectrometer()  # Test the CCS spectrometer
   #test_peristaltic_pump("COM12", 99, "True", "True") 
   #test_hotplate("COM7", 50, 100, "True") 
   #test_relay("COM5", "ON")
   #test_actuator("COM5")