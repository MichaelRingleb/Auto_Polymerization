"""
Device Test Controller for Auto_Polymerization Platform

This module provides comprehensive testing functions for all real devices in the
Auto_Polymerization platform. It allows individual testing of pumps, valves, 
UV-VIS spectrometer, heating/stirring, and linear actuator systems.

Key Features:
    - Individual test functions for each device type
    - Safety checks and user confirmations before critical operations
    - Comprehensive error handling and logging
    - Both simple and complex test scenarios
    - Follows project conventions (using 'target' instead of 'destination')

Device Types Tested:
    - Volumetric pumps (Solvent_Monomer_Modification_Pump, Initiator_CTA_Pump, etc.)
    - Continuous/peristaltic pumps (Polymer_Peri_Pump, Solvent_Peri_Pump)
    - Analytical pump (Analytical_Pump)
    - Gas and solenoid valves
    - UV-VIS spectrometer
    - Heating and stirring system
    - Linear actuator for vial positioning

Usage:
    python device_test_controller.py

Author: Assistant
Date: [Current Date]
Version: 1.0
"""

import sys
import os
import logging
from pathlib import Path
import time
from typing import Optional, Tuple, Dict, Any, Union

# Add the project root to the path for imports (demo folder is one level down)
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from medusa import Medusa
import src.UV_VIS.uv_vis_utils as uv_vis

# Setup logging
logger = logging.getLogger("device_test")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class DeviceTestController:
    """Main controller class for testing all devices in the Auto_Polymerization platform."""
    
    def __init__(self, layout_path: str):
        """
        Initialize the device test controller.
        
        Args:
            layout_path (str): Path to the Medusa design JSON file
        """
        self.layout_path = Path(layout_path)
        self.medusa = None
        self.test_results = {}
        
        # Test parameters
        self.test_volume = 1.0  # mL
        self.test_temperature = 25  # °C
        self.test_rpm = 100
        self.test_transfer_rate = 0.5  # mL/min
        
    def initialize_medusa(self) -> bool:
        """
        Initialize the Medusa system.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing Medusa with layout: {self.layout_path}")
            
            # Check if layout file exists
            if not self.layout_path.exists():
                logger.error(f"Layout file not found: {self.layout_path}")
                return False
            
            # Check if layout file is valid JSON
            try:
                import json
                with open(self.layout_path, 'r') as f:
                    json.load(f)
                logger.info("Layout file is valid JSON")
            except json.JSONDecodeError as e:
                logger.error(f"Layout file is not valid JSON: {e}")
                return False
            
            # List available COM ports for debugging
            self.list_available_ports()
            
            self.medusa = Medusa(
                graph_layout=self.layout_path,
                logger=logger
            )
            logger.info("Medusa initialization successful")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Medusa: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def user_confirmation(self, message: str) -> bool:
        """
        Get user confirmation for potentially dangerous operations.
        
        Args:
            message (str): Message to display to user
            
        Returns:
            bool: True if user confirms, False otherwise
        """
        response = input(f"\n{message} (y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    def _check_medusa_initialized(self) -> bool:
        """
        Check if Medusa is properly initialized.
        
        Returns:
            bool: True if medusa is initialized, False otherwise
        """
        if self.medusa is None:
            logger.error("Medusa is not initialized. Please call initialize_medusa() first.")
            return False
        return True
    
    def list_available_ports(self) -> None:
        """List all available COM ports for debugging."""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            logger.info("Available COM ports:")
            for port in ports:
                logger.info(f"  {port.device}: {port.description}")
        except ImportError:
            logger.warning("pyserial not available, cannot list ports")
        except Exception as e:
            logger.error(f"Error listing ports: {e}")
    
    def test_syringe_pump(self, pump_id: str, source: str, target: str, 
                         volume: Optional[float] = None) -> Dict[str, Any]:
        """
        Test a syringe pump with a small transfer.
        
        Args:
            pump_id (str): ID of the pump to test
            source (str): Source vessel
            target (str): Target vessel
            volume (float): Volume to transfer (uses test_volume if None)
            
        Returns:
            Dict[str, Any]: Test results
        """
        if volume is None:
            volume = self.test_volume
            
        logger.info(f"Testing syringe pump: {pump_id}")
        logger.info(f"Transfer {volume} mL from {source} to {target}")
        
        if not self.user_confirmation(f"Proceed with testing {pump_id}?"):
            return {"success": False, "reason": "User cancelled"}
        
        if not self._check_medusa_initialized():
            return {"success": False, "error": "Medusa not initialized"}
        
        # Type assertion to help the type checker
        assert self.medusa is not None
        
        try:
            start_time = time.time()
            self.medusa.transfer_volumetric(
                source=source,
                target=target,
                pump_id=pump_id,
                volume=volume,
                transfer_type="liquid"
            )
            end_time = time.time()
            
            duration = end_time - start_time
            logger.info(f"Syringe pump test completed in {duration:.2f} seconds")
            
            return {
                "success": True,
                "pump_id": pump_id,
                "volume": volume,
                "duration": duration,
                "source": source,
                "target": target
            }
            
        except Exception as e:
            logger.error(f"Syringe pump test failed: {e}")
            return {"success": False, "error": str(e), "pump_id": pump_id}
    
    def test_peristaltic_pump(self, pump_id: str, source: str, target: str,
                             duration: int = 10) -> Dict[str, Any]:
        """
        Test a peristaltic pump.
        
        Args:
            pump_id (str): ID of the pump to test
            source (str): Source vessel
            target (str): Target vessel
            duration (int): Test duration in seconds
            
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info(f"Testing peristaltic pump: {pump_id}")
        logger.info(f"Run for {duration} seconds from {source} to {target}")
        
        if not self.user_confirmation(f"Proceed with testing {pump_id}?"):
            return {"success": False, "reason": "User cancelled"}
        
        if not self._check_medusa_initialized():
            return {"success": False, "error": "Medusa not initialized"}
        
        # Type assertion to help the type checker
        assert self.medusa is not None
        
        try:
            # Start continuous transfer
            self.medusa.transfer_continuous(
                source=source,
                target=target,
                pump_id=pump_id,
                direction_CW=True,
                transfer_rate=self.test_transfer_rate
            )
            
            logger.info(f"Peristaltic pump started. Running for {duration} seconds...")
            time.sleep(duration)
            
            # Stop the pump
            self.medusa.transfer_continuous(
                source=source,
                target=target,
                pump_id=pump_id,
                direction_CW=False,
                transfer_rate=0
            )
            
            logger.info("Peristaltic pump test completed")
            
            return {
                "success": True,
                "pump_id": pump_id,
                "duration": duration,
                "transfer_rate": self.test_transfer_rate,
                "source": source,
                "target": target
            }
            
        except Exception as e:
            logger.error(f"Peristaltic pump test failed: {e}")
            return {"success": False, "error": str(e), "pump_id": pump_id}
    
    def test_gas_valve(self) -> Dict[str, Any]:
        """
        Test gas valve control.
        
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info("Testing gas valve control")
        
        if not self.user_confirmation("Proceed with gas valve test?"):
            return {"success": False, "reason": "User cancelled"}
        
        if not self._check_medusa_initialized():
            return {"success": False, "error": "Medusa not initialized"}
        
        # Type assertion to help the type checker
        assert self.medusa is not None
        
        try:
            # Open gas valve
            logger.info("Opening gas valve...")
            self.medusa.write_serial("COM12", "GAS_ON")
            time.sleep(2)
            
            # Close gas valve
            logger.info("Closing gas valve...")
            self.medusa.write_serial("COM12", "GAS_OFF")
            time.sleep(2)
            
            logger.info("Gas valve test completed")
            
            return {
                "success": True,
                "operation": "gas_valve_cycle",
                "commands": ["GAS_ON", "GAS_OFF"]
            }
            
        except Exception as e:
            logger.error(f"Gas valve test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_solenoid_valve(self) -> Dict[str, Any]:
        """
        Test solenoid valve control for precipitation.
        
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info("Testing solenoid valve control")
        
        if not self.user_confirmation("Proceed with solenoid valve test?"):
            return {"success": False, "reason": "User cancelled"}
        
        if not self._check_medusa_initialized():
            return {"success": False, "error": "Medusa not initialized"}
        
        # Type assertion to help the type checker
        assert self.medusa is not None
        
        try:
            # Open solenoid valve
            logger.info("Opening solenoid valve...")
            self.medusa.write_serial("COM12", "PRECIP_ON")
            time.sleep(2)
            
            # Close solenoid valve
            logger.info("Closing solenoid valve...")
            self.medusa.write_serial("COM12", "PRECIP_OFF")
            time.sleep(2)
            
            logger.info("Solenoid valve test completed")
            
            return {
                "success": True,
                "operation": "solenoid_valve_cycle",
                "commands": ["PRECIP_ON", "PRECIP_OFF"]
            }
            
        except Exception as e:
            logger.error(f"Solenoid valve test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_linear_actuator(self) -> Dict[str, Any]:
        """
        Test linear actuator for vial positioning.
        
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info("Testing linear actuator")
        
        if not self.user_confirmation("Proceed with linear actuator test?"):
            return {"success": False, "reason": "User cancelled"}
        
        if not self._check_medusa_initialized():
            return {"success": False, "error": "Medusa not initialized"}
        
        # Type assertion to help the type checker
        assert self.medusa is not None
        
        try:
            # Move to position 1000 (lower position)
            logger.info("Moving actuator to position 1000...")
            self.medusa.write_serial("COM12", "1000")
            time.sleep(3)
            
            # Move to position 2000 (upper position)
            logger.info("Moving actuator to position 2000...")
            self.medusa.write_serial("COM12", "2000")
            time.sleep(3)
            
            logger.info("Linear actuator test completed")
            
            return {
                "success": True,
                "operation": "actuator_cycle",
                "positions": [1000, 2000]
            }
            
        except Exception as e:
            logger.error(f"Linear actuator test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_heating_stirring(self, vessel: str = "Reaction_Vial") -> Dict[str, Any]:
        """
        Test heating and stirring system.
        
        Args:
            vessel (str): Vessel to test
            
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info(f"Testing heating and stirring for {vessel}")
        
        if not self.user_confirmation(f"Proceed with heating/stirring test for {vessel}?"):
            return {"success": False, "reason": "User cancelled"}
        
        if not self._check_medusa_initialized():
            return {"success": False, "error": "Medusa not initialized"}
        
        # Type assertion to help the type checker
        assert self.medusa is not None
        
        try:
            # Start heating and stirring
            logger.info(f"Starting heating to {self.test_temperature}°C and stirring at {self.test_rpm} RPM...")
            self.medusa.heat_stir(
                vessel=vessel,
                temperature=self.test_temperature,
                rpm=self.test_rpm
            )
            
            # Monitor temperature for 30 seconds
            logger.info("Monitoring temperature for 30 seconds...")
            start_time = time.time()
            temperatures = []
            
            while time.time() - start_time < 30:
                try:
                    temp = self.medusa.get_hotplate_temperature(vessel)
                    temperatures.append(temp)
                    logger.info(f"Current temperature: {temp}°C")
                    time.sleep(5)
                except Exception as e:
                    logger.warning(f"Could not read temperature: {e}")
                    break
            
            # Stop heating and stirring
            logger.info("Stopping heating and stirring...")
            self.medusa.heat_stir(vessel=vessel, temperature=0, rpm=0)
            
            logger.info("Heating and stirring test completed")
            
            return {
                "success": True,
                "vessel": vessel,
                "target_temperature": self.test_temperature,
                "target_rpm": self.test_rpm,
                "temperature_readings": temperatures,
                "monitoring_duration": 30
            }
            
        except Exception as e:
            logger.error(f"Heating and stirring test failed: {e}")
            return {"success": False, "error": str(e), "vessel": vessel}
    
    def test_uv_vis_spectrometer(self) -> Dict[str, Any]:
        """
        Test UV-VIS spectrometer.
        
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info("Testing UV-VIS spectrometer")
        
        if not self.user_confirmation("Proceed with UV-VIS spectrometer test?"):
            return {"success": False, "reason": "User cancelled"}
        
        try:
            # Take a reference spectrum
            logger.info("Taking reference spectrum...")
            spectrum, wavelengths, filename, _, _ = uv_vis.take_spectrum(reference=True)
            
            if spectrum is not None and wavelengths is not None:
                logger.info(f"Reference spectrum taken successfully: {filename}")
                logger.info(f"Spectrum shape: {spectrum.shape}")
                logger.info(f"Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")
                
                return {
                    "success": True,
                    "operation": "reference_spectrum",
                    "filename": filename,
                    "spectrum_shape": spectrum.shape,
                    "wavelength_range": [float(wavelengths.min()), float(wavelengths.max())]
                }
            else:
                logger.error("Failed to acquire spectrum")
                return {"success": False, "error": "No spectrum acquired"}
                
        except Exception as e:
            logger.error(f"UV-VIS spectrometer test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_complete_workflow_simulation(self) -> Dict[str, Any]:
        """
        Test a simplified version of the complete workflow.
        
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info("Testing complete workflow simulation")
        
        if not self.user_confirmation("Proceed with complete workflow simulation?"):
            return {"success": False, "reason": "User cancelled"}
        
        workflow_results = {}
        
        try:
            # 1. Test gas valve
            logger.info("Step 1: Testing gas valve...")
            workflow_results["gas_valve"] = self.test_gas_valve()
            
            # 2. Test heating and stirring
            logger.info("Step 2: Testing heating and stirring...")
            workflow_results["heating_stirring"] = self.test_heating_stirring()
            
            # 3. Test linear actuator
            logger.info("Step 3: Testing linear actuator...")
            workflow_results["linear_actuator"] = self.test_linear_actuator()
            
            # 4. Test syringe pump
            logger.info("Step 4: Testing syringe pump...")
            workflow_results["syringe_pump"] = self.test_syringe_pump(
                "Solvent_Monomer_Modification_Pump",
                "Solvent_Vessel",
                "Waste_Vessel",
                volume=0.5
            )
            
            # 5. Test UV-VIS spectrometer
            logger.info("Step 5: Testing UV-VIS spectrometer...")
            workflow_results["uv_vis"] = self.test_uv_vis_spectrometer()
            
            # 6. Test solenoid valve
            logger.info("Step 6: Testing solenoid valve...")
            workflow_results["solenoid_valve"] = self.test_solenoid_valve()
            
            # Calculate overall success
            successful_tests = sum(1 for result in workflow_results.values() if result.get("success", False))
            total_tests = len(workflow_results)
            
            logger.info(f"Workflow simulation completed: {successful_tests}/{total_tests} tests successful")
            
            return {
                "success": successful_tests == total_tests,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "results": workflow_results
            }
            
        except Exception as e:
            logger.error(f"Complete workflow simulation failed: {e}")
            return {"success": False, "error": str(e), "results": workflow_results}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all individual device tests.
        
        Returns:
            Dict[str, Any]: Results of all tests
        """
        logger.info("Starting comprehensive device testing...")
        
        if not self.initialize_medusa():
            return {"success": False, "error": "Failed to initialize Medusa"}
        
        all_results = {}
        
        # Test each device type
        test_functions = [
            ("gas_valve", self.test_gas_valve),
            ("solenoid_valve", self.test_solenoid_valve),
            ("linear_actuator", self.test_linear_actuator),
            ("heating_stirring", lambda: self.test_heating_stirring()),
            ("uv_vis_spectrometer", self.test_uv_vis_spectrometer),
            ("syringe_pump_solvent", lambda: self.test_syringe_pump("Solvent_Monomer_Modification_Pump", "Solvent_Vessel", "Waste_Vessel")),
            ("syringe_pump_initiator", lambda: self.test_syringe_pump("Initiator_CTA_Pump", "Initiator_Vessel", "Waste_Vessel")),
            ("peristaltic_pump_polymer", lambda: self.test_peristaltic_pump("Polymer_Peri_Pump", "Reaction_Vial", "Reaction_Vial", duration=5)),
        ]
        
        for test_name, test_func in test_functions:
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = test_func()
                all_results[test_name] = result
                
                if result.get("success", False):
                    logger.info(f"✓ {test_name} test PASSED")
                else:
                    logger.error(f"✗ {test_name} test FAILED: {result.get('error', result.get('reason', 'Unknown error'))}")
                    
            except Exception as e:
                logger.error(f"✗ {test_name} test FAILED with exception: {e}")
                all_results[test_name] = {"success": False, "error": str(e)}
        
        # Summary
        successful_tests = sum(1 for result in all_results.values() if result.get("success", False))
        total_tests = len(all_results)
        
        logger.info(f"\n{'='*50}")
        logger.info(f"TESTING SUMMARY: {successful_tests}/{total_tests} tests passed")
        logger.info(f"{'='*50}")
        
        return {
            "success": successful_tests == total_tests,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "results": all_results
        }


def main():
    """Main function to run device tests."""
    print("Auto_Polymerization Device Test Controller")
    print("=" * 50)
    
    # Get layout file path
    layout_path = input("Enter path to Medusa design JSON file: ").strip()
    
    if not layout_path:
        print("No layout file specified. Exiting.")
        return
    
    # Create test controller
    controller = DeviceTestController(layout_path)
    
    # Menu for test options
    while True:
        print("\n" + "="*50)
        print("DEVICE TEST MENU")
        print("="*50)
        print("1. Run all individual device tests")
        print("2. Test complete workflow simulation")
        print("3. Test specific device:")
        print("   a) Gas valve")
        print("   b) Solenoid valve")
        print("   c) Linear actuator")
        print("   d) Heating and stirring")
        print("   e) UV-VIS spectrometer")
        print("   f) Syringe pump")
        print("   g) Peristaltic pump")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            results = controller.run_all_tests()
            print(f"\nAll tests completed: {results['successful_tests']}/{results['total_tests']} passed")
            
        elif choice == "2":
            results = controller.test_complete_workflow_simulation()
            print(f"\nWorkflow simulation completed: {results['successful_tests']}/{results['total_tests']} passed")
            
        elif choice == "3":
            device_choice = input("Select device (a-g): ").strip().lower()
            
            if device_choice == "a":
                controller.test_gas_valve()
            elif device_choice == "b":
                controller.test_solenoid_valve()
            elif device_choice == "c":
                controller.test_linear_actuator()
            elif device_choice == "d":
                controller.test_heating_stirring()
            elif device_choice == "e":
                controller.test_uv_vis_spectrometer()
            elif device_choice == "f":
                pump_id = input("Enter pump ID: ").strip()
                source = input("Enter source vessel: ").strip()
                target = input("Enter target vessel: ").strip()
                controller.test_syringe_pump(pump_id, source, target)
            elif device_choice == "g":
                pump_id = input("Enter pump ID: ").strip()
                source = input("Enter source vessel: ").strip()
                target = input("Enter target vessel: ").strip()
                controller.test_peristaltic_pump(pump_id, source, target)
            else:
                print("Invalid device choice.")
                
        elif choice == "4":
            print("Exiting device test controller.")
            break
            
        else:
            print("Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    main() 