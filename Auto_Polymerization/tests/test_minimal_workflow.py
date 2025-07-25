"""
Minimal Workflow Test Script for Auto_Polymerization
---------------------------------------------------
Tests core workflow functionalities: liquid transfers, hotplate, serial devices, NMR, and UV-Vis integration with preset values.

Usage:
    Run directly to execute all tests sequentially.
    If Medusa object is not provided, attempts to auto-detect .json config in users/config.

Key Features:
- Can be run standalone or called from other modules (with a Medusa object)
- Cleans up only files created during the test run (NMR and UV-Vis)
- Robust logging and error handling
"""

import sys
import os
import logging
import time
from pathlib import Path
import glob
from medusa import Medusa


SLEEP_TIME = 10  # seconds for hardware operations


def _setup_logger(logger=None):
    """
    Set up and return a logger for the test. If a logger is provided, use it; otherwise, create a new one.
    Ensures no duplicate handlers are added.
    """
    if logger is not None:
        return logger
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    return logger


def _find_or_prompt_layout(logger):
    """
    Find a .json config in users/config or prompt the user for a path.
    Returns the path to the layout file as a string.
    """
    config_folder = 'Auto_Polymerization/users/config/'
    if os.path.exists(config_folder):
        for fname in os.listdir(config_folder):
             if fname.endswith('.json'):
                layout_path = os.path.join(config_folder, fname)
                logger.info(f"Found layout JSON: {layout_path}")
                return layout_path
    layout_path = input("Enter path to design .json: ").strip()
    if not layout_path:
        logger.error("No layout path provided. Exiting.")
        sys.exit(1)
    return layout_path


def test_peristaltic_transfers(medusa):
    """
    Test peristaltic pump liquid transfers in both directions.
    Demonstrates starting and stopping flow for each peristaltic pump.
    """
    medusa.logger.info("Testing peristaltic pumps...")
    medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW=False, transfer_rate=20)
    medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW=True, transfer_rate=20)
    time.sleep(SLEEP_TIME)
    medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW=True, transfer_rate=0)
    medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW=False, transfer_rate=0)
    medusa.logger.info("Peristaltic pump test complete.")



def test_hotplate(medusa):
    """
    Test hotplate heating and stirring control.
    Demonstrates setting and stopping temperature and RPM, and reading back values.
    """
    medusa.logger.info("Testing hotplate...")
    medusa.heat_stir(vessel="Reaction_Vial", temperature=20, rpm=200)
    medusa.logger.info(f"Hotplate temperature: {medusa.get_hotplate_temperature('Reaction_Vial')}")
    medusa.logger.info(f"Hotplate RPM: {medusa.get_hotplate_rpm('Reaction_Vial')}")
    time.sleep(SLEEP_TIME)
    medusa.heat_stir(vessel="Reaction_Vial", temperature=0, rpm=0)
    time.sleep(SLEEP_TIME)
    medusa.logger.info(f"Hotplate temperature after stop: {medusa.get_hotplate_temperature('Reaction_Vial')}")
    medusa.logger.info(f"Hotplate RPM after stop: {medusa.get_hotplate_rpm('Reaction_Vial')}")
    time.sleep(SLEEP_TIME)
    medusa.logger.info("Hotplate test complete.")


def test_serial_devices(medusa):
    """
    Test serial device control for actuators and valves.
    Demonstrates sending commands to linear actuator, gas valve, and precipitation valve.
    """
    medusa.logger.info("Testing serial devices...")
    medusa.write_serial("Linear_Actuator", b"2000\n")
    time.sleep(SLEEP_TIME)
    medusa.write_serial("Linear_Actuator", b"1000\n")
    time.sleep(SLEEP_TIME)
    medusa.write_serial("Gas_Valve", b"GAS_ON\n")
    time.sleep(SLEEP_TIME)
    medusa.write_serial("Gas_Valve", b"GAS_OFF\n")
    time.sleep(SLEEP_TIME)
    medusa.write_serial("Precipitation_Valve", b"PRECIP_ON\n")
    time.sleep(SLEEP_TIME)
    medusa.write_serial("Precipitation_Valve", b"PRECIP_OFF\n")
    medusa.logger.info("Serial devices test complete.")


def test_volumetric_transfers(medusa):
    """
    Test syringe pump liquid transfers.
    Demonstrates transferring small volumes from various vessels to waste using different syringe pumps.
    """
    medusa.logger.info("Testing syringe pumps...")
    #max draw and dispense speeds = 0.5 mL/s
    medusa.transfer_volumetric(source="Purge_Solvent_Vessel_2", target="Waste_Vessel", pump_id="Analytical_Pump", 
                                transfer_type="liquid",
                                pre_rinse = 1, pre_rinse_volume = 1.0, pre_rinse_speed = 0.2,
                                volume=1.0, draw_speed = 0.1, dispense_speed = 0.2,  
                                flush = 1, flush_volume = 2, flush_speed = 0.3,  
                                post_rinse = 1, post_rinse_vessel = "Purge_Solvent_Vessel_2", post_rinse_volume = 1.0, post_rinse_speed = 0.1
                                )  
    
    medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Precipitation_Pump", 
                                transfer_type="liquid",
                                pre_rinse = 1, pre_rinse_volume = 1.0, pre_rinse_speed = 0.2,
                                volume=1.0, draw_speed = 0.1, dispense_speed = 0.2,  
                                flush = 1, flush_volume = 2, flush_speed = 0.3,  
                                post_rinse = 1, post_rinse_vessel = "Purge_Solvent_Vessel_1", post_rinse_volume = 1.0, post_rinse_speed = 0.1
                                )  
    
    medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", 
                                transfer_type="liquid",
                                pre_rinse = 1, pre_rinse_volume = 1.0, pre_rinse_speed = 0.2,
                                volume=1.0, draw_speed = 0.1, dispense_speed = 0.2,  
                                flush = 1, flush_volume = 2, flush_speed = 0.3,  
                                post_rinse = 1, post_rinse_vessel = "Purge_Solvent_Vessel_1", post_rinse_volume = 1.0, post_rinse_speed = 0.1
                                )  
        
    medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", 
                                transfer_type="liquid",
                                pre_rinse = 1, pre_rinse_volume = 1.0, pre_rinse_speed = 0.2,
                                volume=1.0, draw_speed = 0.1, dispense_speed = 0.2,  
                                flush = 1, flush_volume = 2, flush_speed = 0.3,  
                                post_rinse = 1, post_rinse_vessel = "Purge_Solvent_Vessel_1", post_rinse_volume = 1.0, post_rinse_speed = 0.1
                                )  
    medusa.logger.info("Syringe pump test complete.")


def run_minimal_workflow_test(medusa=None, logger=None):
    """
    Run the minimal workflow test. Uses provided medusa object or instantiates as needed.
    If medusa is not provided, tries to find a .json config in users/config, else prompts the user.
    Tracks and deletes only NMR and UV-Vis files created during the test run.
    """
    
    logger = _setup_logger(logger)
    if medusa is None:
        layout_path = _find_or_prompt_layout(logger)
        # from medusa import Medusa
        medusa = Medusa(graph_layout=Path(layout_path), logger=logger)
    import src.NMR.nmr_utils as nmr
    import src.UV_VIS.uv_vis_utils as uv_vis

    # Record files before test for cleanup
    nmr_data_dir = 'Auto_Polymerization/users/data/NMR_data'
    uvvis_data_dir = 'Auto_Polymerization/users/data/UV_VIS_data'
    nmr_files_before = set(glob.glob(os.path.join(nmr_data_dir, '*')))
    uvvis_files_before = set(glob.glob(os.path.join(uvvis_data_dir, '*')))

    logger.info("Start of minimal workflow test")
    # Run all hardware and workflow tests
    test_peristaltic_transfers(medusa)
    test_hotplate(medusa)
    test_serial_devices(medusa)
    test_volumetric_transfers(medusa)
    logger.info("Testing NMR spectrum acquisition...")
    try:
        nmr.acquire_nmr_spectrum(medusa=medusa)
    except Exception as e:
        logger.warning("SOMETHING WENT WRONG, PLEASE CHECK IF THE NMR-SPECTROMETER IS CONNECTED AND REMOTE CONTROL IS ENABLED.")
    logger.info("NMR spectrum acquisition test complete.")
    logger.info("Testing UV-Vis spectrum acquisition...")
    uv_vis.take_spectrum(reference=True)
    logger.info("UV-Vis spectrum acquisition test complete.")
    logger.info("==== All tests completed successfully ====")

    # Wait 10 seconds before cleanup to allow user to inspect files if needed
    time.sleep(10)

    # Cleanup: Delete only files created during this test run
    nmr_files_after = set(glob.glob(os.path.join(nmr_data_dir, '*')))
    uvvis_files_after = set(glob.glob(os.path.join(uvvis_data_dir, '*',)))
    nmr_new_files = nmr_files_after - nmr_files_before
    uvvis_new_files = uvvis_files_after - uvvis_files_before

    def delete_files(files, logger, description):
        """Delete a set of files and log the actions."""
        for f in files:
            try:
                os.remove(f)
                logger.info(f"Deleted {description} file: {f}")
            except Exception as e:
                logger.error(f"Failed to delete {description} file {f}: {e}")
        if not files:
            logger.warning(f"No {description} files found for cleanup.")

    delete_files(nmr_new_files, logger, 'NMR data')
    delete_files(uvvis_new_files, logger, 'UV-Vis spectrum')


if __name__ == "__main__":
    # Add project root to path only when running as main script
    project_root = Path(__file__).parent.parent  # Go up from tests/ to Auto_Polymerization/
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    run_minimal_workflow_test()






