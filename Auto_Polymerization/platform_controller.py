
"""
import yaml
import os

base_dir = os.path.dirname(__file__)
config_path = os.path.join(base_dir, "config.yaml")

with open(config_path, "r") as f:
    config = yaml.safe_load(f)
"""
import sys
import os
import logging
from pathlib import Path
from medusa import Medusa, MedusaDesigner
import time
from linear_actuator_and_valves_control import move_actuator, set_valve


#Setup logging for Medusa liquid transfers
logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


layout = input("Design .json path\n") 
medusa = Medusa(
    graph_layout=layout,
    logger=logger     
)"""
#ideally put into its own module, but for now just import here
# Definition of added volumes and reaction temperature by user before reaction:
"""
Solvent_volume= 10 
Solvent_draw_speed = Solvent_volume / 2  # draw speed in mL/min
Monomer_volume=4
Monomer_draw_speed = Monomer_volume / 2  # draw speed in mL/min
Initiator_volume = 3
Initiator__draw_speed = Initiator_volume / 2  # draw speed in mL/min
CTA_volume= 4
CTA_draw_speed = CTA_volume / 2  # draw speed in mL/min
Polymerization_temp= 20
set_rpm = 200


Functionalization_temp = 20  # Temperature for functionalization step
Functionanilzation_volume = 2 # Volume for functionalization step
Functionalization_draw_speed = Functionanilzation_volume / 2  # draw speed in mL/min


#take the reaction vial out of the heatplate
move_actuator("COM12", "2000")  # Move the reaction vial out of the heatplate

# preheat heatplate
medusa.heat_stir(vessel="Reaction_Vial", temperature= Polymerization_temp, rpm= set_rpm)

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
medusa.transfer_volumetric(source="Solvent_Vessel", destination="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= Solvent_volume, transfer_type="liquid", flush=3, draw_speed=Solvent_draw_speed)
medusa.transfer_volumetric(source="Monomer_Vessel", destination="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= Monomer_volume, transfer_type="liquid", flush=3, draw_speed=Monomer_draw_speed)
medusa.transfer_volumetric(source="Initiator_Vessel", destination="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= Initiator_volume, transfer_type="liquid",flush=3, draw_speed = Initiator__draw_speed)
medusa.transfer_volumetric(source="CTA_Vessel", destination="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= CTA_volume, transfer_type="liquid",flush=3, draw_speed = CTA_draw_speed)

# wait for heat plate to reach x degree (defined earlier)
    # still needs to be implemented


# Lower vial into heat plate
    # still needs to be implemented


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
        # Functionality needs to be embedded here still

    # Start peristaltic pumps   
        # Functionality needs to be embedded here still

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




medusa.transfer_volumetric(source="Gas Reservoir Vessel", destination = "Waste_Vessel", pump_id="Analytical_Pump", volume=1,flush=0,transfer_type="gas")
