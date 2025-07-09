"""
Simple test script to verify medusa syntax and identify issues.

This script tests the basic medusa calls that are used in the device test controller
to ensure they work correctly with the actual medusa API.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from medusa import Medusa

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_medusa_syntax():
    """Test basic medusa syntax to identify issues."""
    
    print("Testing Medusa Syntax")
    print("=" * 50)
    
    # Get layout file path
    layout_path = input("Enter path to your Medusa design JSON file: ").strip()
    
    if not layout_path:
        print("No layout file provided. Using default path...")
        layout_path = "../users/config/fluidic_design_autopoly.json"
    
    try:
        # Initialize medusa
        print(f"Initializing medusa with layout: {layout_path}")
        medusa = Medusa(
            graph_layout=Path(layout_path),
            logger=logger
        )
        print("✓ Medusa initialization successful")
        
        # Test 1: Basic transfer_volumetric call
        print("\nTest 1: transfer_volumetric syntax")
        try:
            # Test the exact syntax used in device test controller
            medusa.transfer_volumetric(
                source="Solvent_Vessel",
                target="Waste_Vessel",
                pump_id="Solvent_Monomer_Modification_Pump",
                volume=0.1,
                transfer_type="liquid",
                flush=1,
                draw_speed=0.05,
                dispense_speed=0.05
            )
            print("✓ transfer_volumetric call successful")
        except Exception as e:
            print(f"✗ transfer_volumetric call failed: {e}")
            print(f"  Error type: {type(e).__name__}")
        
        # Test 2: Basic heat_stir call
        print("\nTest 2: heat_stir syntax")
        try:
            medusa.heat_stir(
                vessel="Reaction_Vial",
                temperature=25,
                rpm=100
            )
            print("✓ heat_stir call successful")
        except Exception as e:
            print(f"✗ heat_stir call failed: {e}")
            print(f"  Error type: {type(e).__name__}")
        
        # Test 3: get_hotplate_temperature call
        print("\nTest 3: get_hotplate_temperature syntax")
        try:
            temp = medusa.get_hotplate_temperature("Reaction_Vial")
            print(f"✓ get_hotplate_temperature call successful: {temp}°C")
        except Exception as e:
            print(f"✗ get_hotplate_temperature call failed: {e}")
            print(f"  Error type: {type(e).__name__}")
        
        # Test 4: get_hotplate_rpm call (might not exist)
        print("\nTest 4: get_hotplate_rpm syntax")
        try:
            rpm = medusa.get_hotplate_rpm("Reaction_Vial")
            print(f"✓ get_hotplate_rpm call successful: {rpm} RPM")
        except Exception as e:
            print(f"✗ get_hotplate_rpm call failed: {e}")
            print(f"  Error type: {type(e).__name__}")
            print("  Note: This method might not exist in the medusa API")
        
        # Test 5: transfer_continuous call
        print("\nTest 5: transfer_continuous syntax")
        try:
            medusa.transfer_continuous(
                source="Reaction_Vial",
                target="Reaction_Vial",
                pump_id="Polymer_Peri_Pump",
                direction_CW=True,
                transfer_rate=0.5
            )
            print("✓ transfer_continuous call successful")
            
            # Stop the pump
            medusa.transfer_continuous(
                source="Reaction_Vial",
                target="Reaction_Vial",
                pump_id="Polymer_Peri_Pump",
                direction_CW=False,
                transfer_rate=0
            )
            print("✓ transfer_continuous stop call successful")
        except Exception as e:
            print(f"✗ transfer_continuous call failed: {e}")
            print(f"  Error type: {type(e).__name__}")
        
        # Test 6: write_serial call
        print("\nTest 6: write_serial syntax")
        try:
            medusa.write_serial("COM12", "GAS_ON")
            print("✓ write_serial call successful")
        except Exception as e:
            print(f"✗ write_serial call failed: {e}")
            print(f"  Error type: {type(e).__name__}")
        
        print("\n" + "=" * 50)
        print("Syntax test completed!")
        print("Check the results above to identify any issues with medusa calls.")
        
    except Exception as e:
        print(f"✗ Medusa initialization failed: {e}")
        print(f"  Error type: {type(e).__name__}")


if __name__ == "__main__":
    test_medusa_syntax() 