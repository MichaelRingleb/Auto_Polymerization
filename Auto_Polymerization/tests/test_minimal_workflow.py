"""
Minimal Medusa Workflow Test

This script checks basic workflow functionalities:
- Heat/stir the reaction vial
- Read hotplate temperature and RPM
- Perform a simple volumetric pump transfer
- Test UV-VIS spectrometer (reference spectrum)
- Test peristaltic pump (Polymer_Peri_Pump)

Usage:
    python test_minimal_workflow.py
"""

import time
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from medusa import Medusa

# Try to import UV-VIS utils if available
try:
    import src.UV_VIS.uv_vis_utils as uv_vis
    UV_VIS_AVAILABLE = True
except ImportError:
    UV_VIS_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medusa_test")

def main():
    layout_path = r"D:\Documents\autopoly\Auto_Polymerization\Auto_Polymerization\users\config\fluidic_design_autopoly copy.json"  # Adjust if needed

    try:
        medusa = Medusa(
            graph_layout=Path(layout_path),
            logger=logger
        )
        print("Medusa initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Medusa: {e}")
        return

    print("Testing heat/stir...")
    try:
        medusa.heat_stir(vessel="Reaction_Vial", temperature=25, rpm=100)
        temp = medusa.get_hotplate_temperature("Reaction_Vial")
        print(f"Hotplate temperature: {temp}")
        time.sleep(5)
        try:
            rpm = medusa.get_hotplate_rpm("Reaction_Vial")
            print(f"Hotplate RPM: {rpm}")
        except Exception as e:
            print(f"Could not read RPM: {e}")
        time.sleep(5)
        medusa.heat_stir(vessel="Reaction_Vial", temperature=0, rpm=0)
    except Exception as e:
        print(f"Heat/stir test failed: {e}")
    time.sleep(5)


    print("\nTesting SerialDevice commands (Gas, Precipitation, Linear Actuator)...")
    serial_tests = [
        ("Gas valve ON", "COM12", "GAS_ON\n"),
        ("Gas valve OFF", "COM12", "GAS_OFF\n"),
        ("Precipitation valve ON", "COM12", "PRECIP_ON\n"),
        ("Precipitation valve OFF", "COM12", "PRECIP_OFF\n"),
        ("Linear actuator to position 1000", "COM12", "1000\n"),
        ("Linear actuator to position 2000", "COM12", "2000\n"),
    ]
    for desc, com_port, command in serial_tests:
        print(f"Testing: {desc} ({com_port}, {command})")
        try:
            medusa.write_serial(com_port, command)
            print(f"{desc} command sent successfully.")
            time.sleep(10)  # Increased wait time for hardware response
        except Exception as e:
            print(f"{desc} command failed: {e}")
    time.sleep(5)

    print("Done.")

if __name__ == "__main__":
    main() 