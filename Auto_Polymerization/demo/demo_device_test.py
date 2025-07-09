"""
Demo script for device testing in Auto_Polymerization platform.

This script demonstrates how to use the DeviceTestController to test
individual devices and complete workflows.

Usage:
    python demo_device_test.py

Example:
    This script will test a few key devices with safe parameters.
"""

import sys
from pathlib import Path

# Add the project root to the path (demo folder is one level down)
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from demo.device_test_controller import DeviceTestController
import logging

# Setup logging for demo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_individual_tests():
    """Demonstrate individual device tests."""
    print("=" * 60)
    print("DEMO: Individual Device Tests")
    print("=" * 60)
    
    # Get layout file path
    layout_path = input("Enter path to your Medusa design JSON file: ").strip()
    
    if not layout_path:
        print("No layout file provided. Using default path...")
        layout_path = "../users/config/fluidic_design_autopoly.json"
    
    # Create controller
    controller = DeviceTestController(layout_path)
    
    # Initialize Medusa
    if not controller.initialize_medusa():
        print("Failed to initialize Medusa. Exiting demo.")
        return
    
    print("\nDemo will test the following devices:")
    print("1. Gas valve (open/close cycle)")
    print("2. Linear actuator (position changes)")
    print("3. Heat plate only (temperature control)")
    print("4. Stirring only (RPM control)")
    print("5. UV-VIS spectrometer (reference spectrum)")
    print("6. Syringe pump (small transfer)")
    print("7. Polymer peristaltic pump (recirculation)")
    
    proceed = input("\nProceed with demo? (y/N): ").strip().lower()
    if proceed not in ['y', 'yes']:
        print("Demo cancelled.")
        return
    
    # Test 1: Gas valve
    print("\n" + "-" * 40)
    print("TEST 1: Gas Valve")
    print("-" * 40)
    result1 = controller.test_gas_valve()
    print(f"Result: {'PASS' if result1['success'] else 'FAIL'}")
    
    # Test 2: Linear actuator
    print("\n" + "-" * 40)
    print("TEST 2: Linear Actuator")
    print("-" * 40)
    result2 = controller.test_linear_actuator()
    print(f"Result: {'PASS' if result2['success'] else 'FAIL'}")
    
    # Test 3: Heat plate only
    print("\n" + "-" * 40)
    print("TEST 3: Heat Plate Only")
    print("-" * 40)
    result3 = controller.test_heat_plate_only()
    print(f"Result: {'PASS' if result3['success'] else 'FAIL'}")
    
    # Test 4: Stirring only
    print("\n" + "-" * 40)
    print("TEST 4: Stirring Only")
    print("-" * 40)
    result4 = controller.test_stirring_only()
    print(f"Result: {'PASS' if result4['success'] else 'FAIL'}")
    
    # Test 5: UV-VIS spectrometer
    print("\n" + "-" * 40)
    print("TEST 5: UV-VIS Spectrometer")
    print("-" * 40)
    result5 = controller.test_uv_vis_spectrometer()
    print(f"Result: {'PASS' if result5['success'] else 'FAIL'}")
    
    # Test 6: Syringe pump (with safe parameters)
    print("\n" + "-" * 40)
    print("TEST 6: Syringe Pump")
    print("-" * 40)
    result6 = controller.test_syringe_pump(
        pump_id="Solvent_Monomer_Modification_Pump",
        source="Solvent_Vessel",
        target="Waste_Vessel",
        volume=0.5  # Small volume for safety
    )
    print(f"Result: {'PASS' if result6['success'] else 'FAIL'}")
    
    # Test 7: Polymer peristaltic pump
    print("\n" + "-" * 40)
    print("TEST 7: Polymer Peristaltic Pump")
    print("-" * 40)
    result7 = controller.test_polymer_peristaltic_pump()
    print(f"Result: {'PASS' if result7['success'] else 'FAIL'}")
    
    # Summary
    print("\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    results = [result1, result2, result3, result4, result5, result6, result7]
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All demo tests passed!")
    else:
        print("⚠️  Some tests failed. Check the logs for details.")


def demo_workflow_simulation():
    """Demonstrate complete workflow simulation."""
    print("=" * 60)
    print("DEMO: Complete Workflow Simulation")
    print("=" * 60)
    
    # Get layout file path
    layout_path = input("Enter path to your Medusa design JSON file: ").strip()
    
    if not layout_path:
        print("No layout file provided. Using default path...")
        layout_path = "../users/config/fluidic_design_autopoly.json"
    
    # Create controller
    controller = DeviceTestController(layout_path)
    
    # Initialize Medusa
    if not controller.initialize_medusa():
        print("Failed to initialize Medusa. Exiting demo.")
        return
    
    print("\nThis demo will simulate a complete workflow:")
    print("- Gas valve control")
    print("- Heat plate only (temperature control)")
    print("- Stirring only (RPM control)")
    print("- Linear actuator positioning")
    print("- Volumetric pump transfer")
    print("- UV-VIS measurement")
    print("- Solenoid valve control")
    print("- Polymer peristaltic pump (recirculation)")
    print("- Solvent peristaltic pump (flow)")
    
    proceed = input("\nProceed with workflow simulation? (y/N): ").strip().lower()
    if proceed not in ['y', 'yes']:
        print("Demo cancelled.")
        return
    
    # Run workflow simulation
    result = controller.test_complete_workflow_simulation()
    
    # Display results
    print("\n" + "=" * 60)
    print("WORKFLOW SIMULATION RESULTS")
    print("=" * 60)
    
    if result['success']:
        print("🎉 Complete workflow simulation PASSED!")
    else:
        print("⚠️  Workflow simulation had issues.")
    
    print(f"Tests passed: {result['successful_tests']}/{result['total_tests']}")
    
    # Show detailed results
    print("\nDetailed results:")
    for test_name, test_result in result['results'].items():
        status = "PASS" if test_result.get('success', False) else "FAIL"
        print(f"  {test_name}: {status}")


def main():
    """Main demo function."""
    print("Auto_Polymerization Device Test Demo")
    print("=" * 60)
    print("This demo shows how to test real devices in your platform.")
    print("Make sure your hardware is connected and ready before running.")
    print()
    
    while True:
        print("Demo Options:")
        print("1. Individual device tests")
        print("2. Complete workflow simulation")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            demo_individual_tests()
        elif choice == "2":
            demo_workflow_simulation()
        elif choice == "3":
            print("Exiting demo.")
            break
        else:
            print("Invalid choice. Please select 1-3.")


if __name__ == "__main__":
    main() 