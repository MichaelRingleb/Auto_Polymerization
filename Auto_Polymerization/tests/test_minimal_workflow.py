from re import M
import sys
import os
import logging
from pathlib import Path
from medusa import Medusa, MedusaDesigner
import time
import matterlab_nmr as nmr
import matterlab_spectrometers as spectrometer
import src.UV_VIS.uv_vis_utils as uv_vis
#spectrometers still missing


#Setup logging for Medusa liquid transfers
logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
def find_layout_json(config_folder='Auto_Polymerization/users/config/'):
    """
    Search for the first .json file in the config folder and return its path.
    Raises FileNotFoundError if no .json file is found.
    """
    for fname in os.listdir(config_folder):
        if fname.endswith('.json'):
            layout = os.path.join(config_folder, fname)
            print(f"Found layout JSON: {layout}")
            return layout
    raise FileNotFoundError("No .json file found in the config folder.")

layout = input("Design .json path\n") 
medusa = Medusa(
    graph_layout=layout,
    logger=logger     
)



#test code to check the functionality of the different devices
medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW = False, transfer_rate=20)
medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW = True, transfer_rate=20)
time.sleep(10)
medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW = True, transfer_rate=0)
medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW = False, transfer_rate=0)

medusa.heat_stir(vessel="Reaction_Vial", temperature= 20, rpm= 200)
medusa.get_hotplate_temperature("Reaction_Vial")
medusa.get_hotplate_rpm("Reaction_Vial")
time.sleep(10)
medusa.heat_stir(vessel="Reaction_Vial", temperature= 0, rpm= 0)
time.sleep(10)
medusa.get_hotplate_temperature("Reaction_Vial")
medusa.get_hotplate_rpm("Reaction_Vial")
time.sleep(10)

medusa.write_serial("Linear_Actuator", b"2000\n")
time.sleep(10)
medusa.write_serial("Linear_Actuator", b"1000\n")
time.sleep(10)
medusa.write_serial("Gas_Valve", b"GAS_ON\n")
time.sleep(10)
medusa.write_serial("Gas_Valve", b"GAS_OFF\n")
time.sleep(10)
medusa.write_serial("Precipitation_Valve", b"PRECIP_ON\n")
time.sleep(10)
medusa.write_serial("Precipitation_Valve", b"PRECIP_OFF\n")


medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Purge_Solvent_Vessel_2", target="Waste_Vessel", pump_id="Analytical_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Precipitation_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= 1, transfer_type="liquid")


#take an nmr spectrum

#take a uv vis spectrum






