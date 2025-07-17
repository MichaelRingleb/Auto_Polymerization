"""
Minimal Workflow Test Script for Auto_Polymerization
---------------------------------------------------
This script demonstrates and tests the core functionalities of the workflow, including:
- Liquid transfers for each of the used pumps
- Hotplate control
- Serial device control (actuators, valves)
- NMR and UV-Vis spectrometer integration

Usage:
    Run this script directly to execute all tests sequentially.
"""

import sys
import os
import logging
from pathlib import Path
from medusa import Medusa, MedusaDesigner
import time
import matterlab_nmr as nmr_spectrometer
import matterlab_spectrometers as uv_vis_spectrometer
import src.UV_VIS.uv_vis_utils as uv_vis
import src.NMR.nmr_utils as nmr

# Setup logging for Medusa liquid transfers and general feedback
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
            logger.info(f"Found layout JSON: {layout}")
            return layout
    raise FileNotFoundError("No .json file found in the config folder.")

def get_layout_path():
    """
    Prompt the user for the design .json path, or auto-detect if left blank.
    Returns a Path object. Exits if the provided path does not exist.
    """
    user_input = input("Enter path to design .json (leave blank to auto-detect): ").strip()
    if user_input:
        layout_path = Path(user_input)
        if not layout_path.exists():
            logger.error(f"Provided path does not exist: {layout_path}")
            sys.exit(1)
        return layout_path
    else:
        layout = find_layout_json()
        return Path(layout)

def test_peristaltic_transfers(medusa):
    """
    Test liquid transfers using peristaltic pumps via medusa.transfer_continuous.
    This function demonstrates starting and stopping flow in both directions for each peristaltic pump.
    """
    logger.info("Testing liquid transfer pumps (peristaltic)...")
    medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW=False, transfer_rate=20)
    medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW=True, transfer_rate=20)
    time.sleep(10)
    medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW=True, transfer_rate=0)
    medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW=False, transfer_rate=0)
    logger.info("Liquid transfer pumps (peristaltic) test complete.")

def test_hotplate(medusa):
    """
    Test hotplate control (heating and stirring) using medusa.heat_stir, get_hotplate_temperature, and get_hotplate_rpm.
    Demonstrates setting and stopping temperature and RPM, and reading back values.
    """
    logger.info("Testing hotplate (heat/stir)...")
    medusa.heat_stir(vessel="Reaction_Vial", temperature=20, rpm=200)
    logger.info(f"Hotplate temperature: {medusa.get_hotplate_temperature('Reaction_Vial')}")
    logger.info(f"Hotplate RPM: {medusa.get_hotplate_rpm('Reaction_Vial')}")
    time.sleep(10)
    medusa.heat_stir(vessel="Reaction_Vial", temperature=0, rpm=0)
    time.sleep(10)
    logger.info(f"Hotplate temperature after stop: {medusa.get_hotplate_temperature('Reaction_Vial')}")
    logger.info(f"Hotplate RPM after stop: {medusa.get_hotplate_rpm('Reaction_Vial')}")
    time.sleep(10)
    logger.info("Hotplate test complete.")

def test_serial_devices(medusa):
    """
    Test serial device control for actuators and valves using medusa.write_serial.
    Demonstrates sending commands to linear actuator, gas valve, and precipitation valve.
    """
    logger.info("Testing serial devices (actuators and valves)...")
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
    logger.info("Serial devices test complete.")

def test_volumetric_transfers(medusa):
    """
    Test liquid transfers using syringe pumps via medusa.transfer_volumetric.
    Demonstrates transferring small volumes from various vessels to waste using different syringe pumps.
    """
    logger.info("Testing volumetric liquid transfers (syringe pumps)...")
    medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume=1, transfer_type="liquid")
    medusa.transfer_volumetric(source="Purge_Solvent_Vessel_2", target="Waste_Vessel", pump_id="Analytical_Pump", volume=1, transfer_type="liquid")
    medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Precipitation_Pump", volume=1, transfer_type="liquid")
    medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume=1, transfer_type="liquid")
    logger.info("Volumetric liquid transfers (syringe pumps) test complete.")

def test_nmr():
    """
    Test NMR spectrum acquisition using nmr.acquire_nmr_spectrum.
    """
    logger.info("Testing NMR spectrum acquisition...")
    nmr.acquire_nmr_spectrum()
    logger.info("NMR spectrum acquisition test complete.")

def test_uv_vis():
    """
    Test UV-Vis spectrum acquisition using uv_vis.take_spectrum.
    """
    logger.info("Testing UV-Vis spectrum acquisition...")
    uv_vis.take_spectrum(reference=True)
    logger.info("UV-Vis spectrum acquisition test complete.")


def main():
    logger.info("==== Minimal Workflow Test Script ====")
    layout_path = get_layout_path()
    logger.info(f"Using design layout: {layout_path}")
    medusa = Medusa(
        graph_layout=layout_path,
        logger=logger
    )
    test_peristaltic_transfers(medusa)
    test_hotplate(medusa)
    test_serial_devices(medusa)
    test_volumetric_transfers(medusa)
    test_nmr()
    test_uv_vis()
    logger.info("==== All tests completed successfully ====")

if __name__ == "__main__":
    main()






