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
    layout_path = r"D:\Documents\autopoly\Auto_Polymerization\Auto_Polymerization\users\config\fluidic_design_autopoly.json"  # Adjust if needed

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

    print("Testing simple pump transfer...")
    try:
        medusa.transfer_volumetric(
            source="Purge_Solvent_Vessel_1",
            target="Waste_Vessel",
            pump_id="Solvent_Monomer_Modification_Pump",
            volume=2,
            transfer_type="liquid"
        )
        print("Pump transfer successful.")
    except Exception as e:
        print(f"Pump transfer failed: {e}")
    time.sleep(5)

    print("Testing peristaltic pump (Polymer_Peri_Pump)...")
    try:
        medusa.transfer_continuous(
            source="Reaction_Vial",
            target="Reaction_Vial",
            pump_id="Polymer_Peri_Pump",
            direction_CW=True,
            transfer_rate=0.5
        )
        print("Peristaltic pump started. Running for 5 seconds...")
        time.sleep(5)
        medusa.transfer_continuous(
            source="Reaction_Vial",
            target="Reaction_Vial",
            pump_id="Polymer_Peri_Pump",
            direction_CW=False,
            transfer_rate=0
        )
        print("Peristaltic pump stopped.")
    except Exception as e:
        print(f"Peristaltic pump test failed: {e}")
    time.sleep(5)

    # Test all syringe and peristaltic pumps with a volumetric transfer
    print("\nTesting volumetric transfer for all pumps...")
    pump_tests = [
        # Syringe pumps
        ("Analytical_Pump", "Purge_Solvent_Vessel_2", "Waste_Vessel"),
        ("Initiator_CTA_Pump", "Purge_Solvent_Vessel_1", "Waste_Vessel"),
        ("Precipitation_Pump", "Purge_Solvent_Vessel_1", "Waste_Vessel"),
        ("Solvent_Monomer_Modification_Pump", "Purge_Solvent_Vessel_1", "Waste_Vessel"),
        # Peristaltic pumps (simulate as volumetric transfer for test)
        ("Polymer_Peri_Pump", "Reaction_Vial", "Reaction_Vial"),
        ("Solvent_Peri_Pump", "Elution_Solvent_Vessel", "Waste_Vessel"),
    ]
    for pump_id, source, target in pump_tests:
        print(f"Testing {pump_id}: {source} → {target}")
        try:
            medusa.transfer_volumetric(
                source=source,
                target=target,
                pump_id=pump_id,
                volume=1.0,
                transfer_type="liquid"
            )
            print(f"{pump_id} transfer successful.")
        except Exception as e:
            print(f"{pump_id} transfer failed: {e}")
    time.sleep(5)

    print("Testing UV-VIS spectrometer...")
    if UV_VIS_AVAILABLE:
        try:
            spectrum, wavelengths, filename, *_ = uv_vis.take_spectrum(reference=True)
            if spectrum is not None and wavelengths is not None:
                print(f"UV-VIS reference spectrum taken: {filename}")
                print(f"Spectrum shape: {spectrum.shape}")
            else:
                print("UV-VIS: No spectrum acquired.")
        except Exception as e:
            print(f"UV-VIS test failed: {e}")
    else:
        print("UV-VIS utils not available. Skipping UV-VIS test.")
    time.sleep(5)

    print("\nTesting SerialDevice commands (Gas, Precipitation, Linear Actuator)...")
    serial_tests = [
        ("Gas valve ON", "COM12", "GAS_ON"),
        ("Gas valve OFF", "COM12", "GAS_OFF"),
        ("Precipitation valve ON", "COM12", "PRECIP_ON"),
        ("Precipitation valve OFF", "COM12", "PRECIP_OFF"),
        ("Linear actuator to position 1000", "COM12", "1000"),
        ("Linear actuator to position 2000", "COM12", "2000"),
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