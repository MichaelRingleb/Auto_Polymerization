
"""
import yaml
import os

base_dir = os.path.dirname(__file__)
config_path = os.path.join(base_dir, "config.yaml")

with open(config_path, "r") as f:
    config = yaml.safe_load(f)
"""
from re import M
import sys
import os
import logging
from pathlib import Path
from medusa import Medusa, MedusaDesigner
import time
from linear_actuator_and_valves_control import move_actuator, set_valve
from matterlab_peristaltic_pump import LongerPeristalticPump    


#Setup logging for Medusa liquid transfers
logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


layout = input("Design .json path\n") 
medusa = Medusa(
    graph_layout=layout,
    logger=logger     
)



polymer_pump = LongerPeristalticPump(com_port="COM15", address=1)
solvent_pump = LongerPeristalticPump(com_port="COM16", address=2)


"""
#ideally put into its own module, but for now just import here
# Definition of added volumes and reaction temperature by user before reaction:
"""
solvent_volume= 10 
solvent_draw_speed = solvent_volume / 2  # draw speed in mL/min
monomer_volume=4
monomer_draw_speed = monomer_volume / 2  # draw speed in mL/min
initiator_volume = 3
initiator_draw_speed = initiator_volume / 2  # draw speed in mL/min
cta_volume= 4
cta_draw_speed = cta_volume / 2  # draw speed in mL/min
polymerization_temp= 20
set_rpm = 200


Functionalization_temp = 20  # Temperature for functionalization step
Functionanilzation_volume = 2 # Volume for functionalization step
Functionalization_draw_speed = Functionanilzation_volume / 2  # draw speed in mL/min


#take the reaction vial out of the heatplate
move_actuator("COM12", "2000")  # Move the reaction vial out of the heatplate

# preheat heatplate
medusa.heat_stir(vessel="Reaction_Vial", temperature= polymerization_temp, rpm= set_rpm)

# open gas valve (in default mode, gas flow will be blocked)
set_valve("COM12","GAS_ON")

# prime tubing (from vial to waste)
medusa.transfer_volumetric(source="Solvent_Vessel", destination="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Monomer_Vessel", destination="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Modification_Vessel", destination="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Initiator_Vessel", destination="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="CTA_Vessel", destination="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= 1, transfer_type="liquid")

# shut gas valve 
set_valve("COM12","GAS_OFF")


#lock and shim NMR
    # pump deuterated solvent to NMR
medusa.transfer_volumetric(source="Deuterated_Solvent", destination="NMR", pump_id="Analytical_Pump", volume=3.5, transfer_type="liquid")
    # lock and shim NMR on deuterated solvent
        # different process, needs to be implemented still
    # pump deuterated solvent back
medusa.transfer_volumetric(source="NMR", destination="Deuterated_Solvent", pump_id="Analytical_Pump", volume=3.5, transfer_type="liquid")


# fill reaction vial with things for reaction and flush it to the vial 
medusa.transfer_volumetric(source="Solvent_Vessel", destination="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= solvent_volume, transfer_type="liquid", flush=3, draw_speed=solvent_draw_speed)
medusa.transfer_volumetric(source="Monomer_Vessel", destination="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= monomer_volume, transfer_type="liquid", flush=3, draw_speed=monomer_draw_speed)
medusa.transfer_volumetric(source="Initiator_Vessel", destination="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= initiator_volume, transfer_type="liquid",flush=3, draw_speed=initiator_draw_speed)
medusa.transfer_volumetric(source="CTA_Vessel", destination="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= cta_volume, transfer_type="liquid",flush=3, draw_speed=cta_draw_speed)

# wait for heat plate to reach x degree (defined earlier)
    # still needs to be implemented


# Lower vial into heat plate
move_actuator("COM12", "1000")
LongerPeristalticPump(com_port="COM15", address=1)

# Wait for NMR feedback regarding conversion before change to next step

    # Every 5 minutes
        # Pump 3 mL from reaction vial to NMR
medusa.transfer_volumetric(source="Reaction_Vial", destination="NMR", pump_id="Analytical_Pump", volume=3,)
        # Take NMR spectrum and evaluate signal at ca. 5.5 ppm with regards to signal intensity of same signal at beginning
        # Pump 3 mL from NMR back to reaction vial and flush rest into vial with argon
medusa.transfer_volumetric(source="NMR", destination="Reaction_Vial", pump_id="Analytical_Pump", volume=3,)      

    # Every ca. 30 minutes
        # pump deuterated solvent to NMR
medusa.transfer_volumetric(source="Deuterated_Solvent", destination="NMR", pump_id="Analytical_Pump", volume=3,)
        # shim NMR on deuterated solvent
            # different process, needs to be implemented still
        # pump deuterated solvent back
medusa.transfer_volumetric(source="NMR", destination="Deuterated_Solvent", pump_id="Analytical_Pump", volume=3,)

# When 80% conversion reached
    # Stop heatplate
medusa.heat_stir("Reaction_Vial", temperature=0)
    # Also remove vial from heatplate with linear actuator
move_actuator("COM12", "2000")

    # Start peristaltic pumps   
polymer_pump.set_pump(on=True, direction=True, rpm=0.7)
solvent_pump.set_pump(on=True, direction=False, rpm=0.7)

    # Every 5 minutes
        # Pump 3 mL from reaction vial to NMR and evaluate "conversion in comparison to last NMR from polzmerization"
medusa.transfer_volumetric(source="Reaction_Vial", destination="NMR", pump_id="Analytical_Pump", volume=3,)
        # Take NMR spectrum and evaluate signal at ca. 5.5 ppm with regards to signal intensity of same signal at beginning
        # Pump 3 mL from NMR back to reaction vial and flush rest into vial with argon
medusa.transfer_volumetric(source="NMR", destination="Reaction_Vial", pump_id="Analytical_Pump", volume=3,)

    # Every ca. 30 minutes
        # pump deuterated solvent to NMR
medusa.transfer_volumetric(source="Deuterated_Solvent", destination="NMR", pump_id="Analytical_Pump", volume=3,transfer_type="liquid")
        # shim NMR on deuterated solvent
            # different process, needs to be implemented still
        # pump deuterated solvent back
medusa.transfer_volumetric(source="NMR", destination="Deuterated_Solvent", pump_id="Analytical_Pump", volume=3,transfer_type="liquid")


#when 90% conversion reached
    # pump peristaltic pump tubing empty for polymer pump in different direction
polymer_pump.set_pump(on=True, direction=False, rpm=0.7)
solvent_pump.set_pump(on=False, direction=False, rpm=0.7)
#wait for 10 minutes
time.sleep(600)
#turn off polymer pump
polymer_pump.set_pump(on=False, direction=False, rpm=0.7)
   

#add functionalization step
#start flow through UV_VIs
#flow will go on until stopped by other command
medusa.transfer_volumetric(source="Reaction_Vial", destination="UV_VIS", pump_id="Analytical_Pump", volume= 2, transfer_type="liquid", flush=3, draw_speed=Functionalization_draw_speed, destination_speed=1)

#add UV_VIS measurement and evaluation (in the beginning without addition and then continously)









