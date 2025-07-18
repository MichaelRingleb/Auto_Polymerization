#test for direct control of the different devices using the matterlab drivers without medusa as an "agent"

import re
import sys
import os
import time
import serial
import serial.tools.list_ports
from matplotlib import pyplot as plt
import yaml


# Add the source directories to sys.path
base_dir = os.path.dirname(__file__)
#pumps_src = os.path.abspath(os.path.join(base_dir, "source", "Pumps", "src"))                   #add Pumps source directory 
#serial_dev_src = os.path.abspath(os.path.join(base_dir, "source", "SerialDevice", "src"))       #add SerialDevice source directory  
actuator_src = os.path.abspath(os.path.join(base_dir, "source", "LinearActuator","src")) #add LinearActuator source directory to sys.path
#hotplate_src = os.path.abspath(os.path.join(base_dir, "source", "Hotplates", "src")) #add Hotplate source directory to sys.path
#spectrometer_src = os.path.abspath(os.path.join(base_dir, "source", "Spectrometers", "src"))
#sys.path.append(pumps_src)
#sys.path.append(serial_dev_src)
sys.path.append(actuator_src)
#sys.path.append(hotplate_src)
#sys.path.append(spectrometer_src)

# Import necessary classes from the modules
from matterlab_pumps.longer_peri import LongerPeristalticPump
from matterlab_pumps.jkem_pump import JKemPump
from matterlab_serial_device.serial_device import SerialDevice, open_close
from matterlab_hotplates.ika_hotplate import IKAHotplate
from linear_actuator_and_valves_control import move_actuator, set_valve
from matterlab_spectrometers.ccs_spectrometer import CCSSpectrometer


# # Load config from YAML
# config_path = os.path.join(base_dir, "config.yml")
# with open(config_path, "r") as f:
#     config = yaml.safe_load(f)


# # Initialize peristaltic pumps as dict
# peristaltic_pumps = {
#     pump_cfg["name"]: LongerPeristalticPump(
#         com_port=pump_cfg["com_port"],
#         address=pump_cfg["address"]
#     )
#     for pump_cfg in config["peristaltic_pumps"]
# }

# # Initialize syringe pumps as dict
# syringe_pumps = {
#     pump_cfg["name"]: JKemPump(
#         com_port=pump_cfg["com_port"],
#         address=pump_cfg["address"],
#         syringe_volume=pump_cfg["syringe_volume"]
#     )
#     for pump_cfg in config["syringe_pumps"]
# }

# # Initialize hotplate
# hotplate = IKAHotplate(com_port=config["hotplate"]["com_port"])

# # Initialize actuator and solenoid valve COM ports
# linear_actuator_port = config["linear_actuator"]["com_port"]
# solenoid_valve_port = config["solenoid_valve"]["com_port"]


# Function to convert string input to boolean
def str_to_bool(s):
    return s.strip().lower() in ("true", "1", "yes", "y")


# Function to test the JKem syringe pump
def test_jkem_pump():
    # Initialize the JKem pump (adjust COM port and address as needed)
    pump = JKemPump(
        com_port="COM7",        # e.g., "COM3" or "COM5" depending on your setup
        address=4,              # Address set in daisy chain (fro left to right: 1 to 7)     
        syringe_volume=1e-2     # Syringe volume in liters (e.g., 10 mL = 1e-2 L)
    )

    # Move the valve to port 2
    pump.move_valve(valve_num=2)
    print("Valve position:", pump.port)

    # Draw and dispense 1.5 mL (move plunger)
    pump.draw_and_dispense(1.5, 2,4,2,2)




# Function to test the peristaltic pump
def test_peristaltic_pump(com_port, rpm_in, direct_in, on_in):
    while True:    
        # Test control of peristaltic pump for the solvent, address referes to the address of the pump on the DIP (see manual from Longer and also DIP panel on the pump)
        pump_solvent = LongerPeristalticPump(com_port="COM15", address=1)   # COM on my PC == 10
        rpm_in= input("pump_solvent rpm:")                              #revolutions per minute on the pump (from 0.1 to 99)
        direct_in = input("pump_solvent direction (True/False):")       #True = clockwise, False = counter-clockwise
        on_in=input("pump_solvent on/off (True/False):")                #True = on, False = off

        pump_solvent.set_pump(on=str_to_bool(on_in), 
              direction=str_to_bool(direct_in), 

              rpm=float(rpm_in)) # Example to set pump on, CCW direction, and 100 RPM
        print(pump_solvent.query_pump())
        
        # Test control of peristaltic pump for the polymer, address referes to the address of the pump on the DIP (see manual from Longer and also DIP panel on the pump)
        pump_polymer = LongerPeristalticPump(com_port="COM16", address=2)  #COM port on my computer == 12
        rpm_in= input("pump_polymer rpm:")                          #revolutions per minute on the pump (from 0.1 to 99)
        direct_in = input("pump_polymer direction (True/False):")   #True = clockwise, False = counter-clockwise
        on_in=input("pump_polymer on/off (True/False):")            #True = on, False = off

        pump_polymer.set_pump(on=str_to_bool(on_in), 
              direction=str_to_bool(direct_in), 
              rpm=float(rpm_in)) # Example to set pump on, CCW direction, and 100 RPM
        print(pump_polymer.query_pump())
    

# Function to test the relays
def test_relays(com_port, relay_pos):
    arduino = serial.Serial(com_port, 9600, timeout=1)      #Open the serial port for communication
    time.sleep(3)                                           #Give Arduino time to reset
  
    if relay_pos == "PRECIP_ON" or relay_pos == "precip_on":              #Turn on the relay -- this will close the normally open (NO) port at the solenoid valve for precipitation
        arduino.write(b"PRECIP_ON\n")                              #Send command to turn on the relay for precipitation to Arduino
    elif relay_pos == "PRECIP_OFF" or relay_pos == "precip_off":          #Turn off the relay -- this will open the normally open (NO) port at the solenoid valve for precipitation
        arduino.write(b"PRECIP_OFF\n")                             #Send command to turn off the relay for precipitation to Arduino 
    elif relay_pos == "GAS_ON" or relay_pos == "gas_on":          #Turn on the relay -- this will close the normally open (NO) port at the solenoid valve for gas
        arduino.write(b"GAS_ON\n")                             #Send command to turn on the relay for gas to Arduino 
    elif relay_pos == "GAS_OFF" or relay_pos == "gas_off":          #Turn off the relay -- this will open the normally open (NO) port at the solenoid valve for precipitation
        arduino.write(b"GAS_OFF\n")                             #Send command to turn off the relay for gas to Arduino 
    elif relay_pos == "ALL_ON" or relay_pos == "all_on":        #Turn on all relays -- this will close the normally open (NO) port at the solenoid valve for precipitation and gas
        arduino.write(b"ALL_ON\n")                             #Send command to turn on all relays to Arduino
    elif relay_pos == "ALL_OFF" or relay_pos == "all_off":      #Turn off all relays -- this will open the normally open (NO) port at the solenoid valve for precipitation and gas
        arduino.write(b"ALL_OFF\n")                            #Send command to turn off all relays to Arduino
    print(relay_pos, "command sent to Arduino")  #Print the command sent to Arduino for confirmation)
    arduino.close()                                         #Close the serial connection after sending the command


# Function to test the linear actuator, moves the actuator to a specified position (1000 = 0%, 2000 = 100% == 10 cm))
def test_actuator(com_port):
    while True:
        actuator_pos = int(input("actuator position (1000 - 2000):"))
        move_actuator(com_port, actuator_pos) 


# Function to test the IKA hotplate
def test_hotplate(com_port, _temp, _rpm, heat_switch):
    hotplate = IKAHotplate(com_port, max_temp=200, max_rpm=1700) #Initialize the hotplate with the specified COM port, max temperature, and max RPM
    hotplate.temp = _temp                                               #Set hotplate temperature
    hotplate.rpm = _rpm                                                 #Set hotplate RPM                                                     #Wait for 5 seconds to allow hotplate to stabilize
    hotplate._heat_switch = heat_switch                                 #Turn off heating
    
   

def test_ccs_spectrometer():
    spec = CCSSpectrometer(
        usb_port="USB",
        device_model="CCS200",
        device_id="M00479664"
    )
    # measure sectrometer spectrum
    spectrum = spec.measure_spectrum(0.01)  # 0.01 Sekunde Integrationszeit
    # load wavelength data
    wavelengths = spec.get_wavelength_data()
    # Plot
    plt.figure()
    plt.plot(wavelengths, spectrum)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title("Measured spectrum")
    plt.grid(True)
    plt.show()
    spec.close_instrument()


if __name__ == "__main__":
   #test_jkem_pump()  
   #test_peristaltic_pump("COM12", 10, "True", "True") 
   #test_hotplate("COM14",20, 0, False)  #for heat_switch: bool
   #test_actuator("COM12")
   test_relays("COM12", "ALL_OFF")
   #test_actuator("COM12")
   #test_ccs_spectrometer()  # Test the CCS spectrometer