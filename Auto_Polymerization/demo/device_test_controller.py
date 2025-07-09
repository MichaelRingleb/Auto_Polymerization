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
                target=target,  # Use 'target' as in platform_controller.py
                pump_id=pump_id,
                volume=volume,
                transfer_type="liquid",
                flush=1,  # Add flush parameter
                draw_speed=volume/2,  # Add draw_speed parameter
                dispense_speed=volume/2  # Add dispense_speed parameter
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
        Test a peristaltic pump with comprehensive flow rate and direction testing.
        
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
            test_results = {
                "pump_id": pump_id,
                "source": source,
                "target": target,
                "tests_performed": [],
                "flow_rates_tested": [],
                "directions_tested": []
            }
            
            # Test 1: Basic forward flow
            logger.info(f"Test 1: Starting forward flow at {self.test_transfer_rate} mL/min...")
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
            
            test_results["tests_performed"].append("forward_flow")
            test_results["flow_rates_tested"].append(self.test_transfer_rate)
            test_results["directions_tested"].append("forward")
            
            # Test 2: Reverse flow
            logger.info(f"Test 2: Starting reverse flow at {self.test_transfer_rate} mL/min...")
            self.medusa.transfer_continuous(
                source=target,
                target=source,
                pump_id=pump_id,
                direction_CW=False,
                transfer_rate=self.test_transfer_rate
            )
            
            logger.info(f"Reverse flow running for {duration//2} seconds...")
            time.sleep(duration // 2)
            
            # Stop the pump
            self.medusa.transfer_continuous(
                source=target,
                target=source,
                pump_id=pump_id,
                direction_CW=False,
                transfer_rate=0
            )
            
            test_results["tests_performed"].append("reverse_flow")
            test_results["directions_tested"].append("reverse")
            
            # Test 3: Different flow rates
            flow_rates = [0.2, 0.8, 1.5]
            for rate in flow_rates:
                logger.info(f"Test 3: Testing flow rate {rate} mL/min...")
                self.medusa.transfer_continuous(
                    source=source,
                    target=target,
                    pump_id=pump_id,
                    direction_CW=True,
                    transfer_rate=rate
                )
                
                logger.info(f"Running at {rate} mL/min for 5 seconds...")
                time.sleep(5)
                
                # Stop the pump
                self.medusa.transfer_continuous(
                    source=source,
                    target=target,
                    pump_id=pump_id,
                    direction_CW=False,
                    transfer_rate=0
                )
                
                test_results["flow_rates_tested"].append(rate)
            
            test_results["tests_performed"].append("variable_flow_rates")
            
            # Test 4: Rapid start/stop cycles
            logger.info("Test 4: Testing rapid start/stop cycles...")
            for i in range(3):
                logger.info(f"Cycle {i+1}/3: Start pump...")
                self.medusa.transfer_continuous(
                    source=source,
                    target=target,
                    pump_id=pump_id,
                    direction_CW=True,
                    transfer_rate=0.5
                )
                time.sleep(2)
                
                logger.info(f"Cycle {i+1}/3: Stop pump...")
                self.medusa.transfer_continuous(
                    source=source,
                    target=target,
                    pump_id=pump_id,
                    direction_CW=False,
                    transfer_rate=0
                )
                time.sleep(1)
            
            test_results["tests_performed"].append("rapid_cycles")
            
            logger.info("Peristaltic pump test completed")
            
            return {
                "success": True,
                **test_results,
                "duration": duration,
                "transfer_rate": self.test_transfer_rate
            }
            
        except Exception as e:
            logger.error(f"Peristaltic pump test failed: {e}")
            return {"success": False, "error": str(e), "pump_id": pump_id}
    
    def test_polymer_peristaltic_pump(self) -> Dict[str, Any]:
        """
        Test the polymer peristaltic pump specifically.
        
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info("Testing Polymer Peristaltic Pump")
        
        return self.test_peristaltic_pump(
            pump_id="Polymer_Peri_Pump",
            source="Reaction_Vial",
            target="Reaction_Vial",  # Recirculation test
            duration=8
        )
    
    def test_solvent_peristaltic_pump(self) -> Dict[str, Any]:
        """
        Test the solvent peristaltic pump specifically.
        
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info("Testing Solvent Peristaltic Pump")
        
        return self.test_peristaltic_pump(
            pump_id="Solvent_Peri_Pump",
            source="Elution_Solvent_Vessel",
            target="Waste_Vessel",
            duration=8
        )
    
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
        Test heating and stirring system with comprehensive temperature monitoring.
        
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
            # Test 1: Start heating and stirring
            logger.info(f"Starting heating to {self.test_temperature}°C and stirring at {self.test_rpm} RPM...")
            self.medusa.heat_stir(
                vessel=vessel,
                temperature=self.test_temperature,
                rpm=self.test_rpm
            )
            
            # Test 2: Monitor temperature for 30 seconds
            logger.info("Monitoring temperature for 30 seconds...")
            start_time = time.time()
            temperatures = []
            stirring_status = []
            
            while time.time() - start_time < 30:
                try:
                    temp = self.medusa.get_hotplate_temperature(vessel)
                    temperatures.append(temp)
                    logger.info(f"Current temperature: {temp}°C")
                    
                    # Check stirring status (if available) - this method might not exist
                    try:
                        rpm = self.medusa.get_hotplate_rpm(vessel)
                        stirring_status.append(rpm)
                        logger.info(f"Current RPM: {rpm}")
                    except Exception as e:
                        logger.debug(f"Could not read RPM (method may not exist): {e}")
                    
                    time.sleep(5)
                except Exception as e:
                    logger.warning(f"Could not read temperature: {e}")
                    break
            
            # Test 3: Test temperature ramp (if supported)
            logger.info("Testing temperature ramp to 35°C...")
            self.medusa.heat_stir(
                vessel=vessel,
                temperature=35,
                rpm=self.test_rpm
            )
            time.sleep(10)
            
            # Test 4: Test stirring speed change
            logger.info("Testing stirring speed change to 200 RPM...")
            self.medusa.heat_stir(
                vessel=vessel,
                temperature=35,
                rpm=200
            )
            time.sleep(10)
            
            # Test 5: Stop heating and stirring
            logger.info("Stopping heating and stirring...")
            self.medusa.heat_stir(vessel=vessel, temperature=0, rpm=0)
            
            logger.info("Heating and stirring test completed")
            
            return {
                "success": True,
                "vessel": vessel,
                "target_temperature": self.test_temperature,
                "target_rpm": self.test_rpm,
                "temperature_readings": temperatures,
                "stirring_readings": stirring_status if stirring_status else None,
                "monitoring_duration": 30,
                "tests_performed": [
                    "heating_startup",
                    "temperature_monitoring", 
                    "temperature_ramp",
                    "stirring_speed_change",
                    "system_shutdown"
                ]
            }
            
        except Exception as e:
            logger.error(f"Heating and stirring test failed: {e}")
            return {"success": False, "error": str(e), "vessel": vessel}
    
    def test_heat_plate_only(self, vessel: str = "Reaction_Vial") -> Dict[str, Any]:
        """
        Test heat plate functionality without stirring.
        
        Args:
            vessel (str): Vessel to test
            
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info(f"Testing heat plate only for {vessel}")
        
        if not self.user_confirmation(f"Proceed with heat plate test for {vessel}?"):
            return {"success": False, "reason": "User cancelled"}
        
        if not self._check_medusa_initialized():
            return {"success": False, "error": "Medusa not initialized"}
        
        # Type assertion to help the type checker
        assert self.medusa is not None
        
        try:
            # Test 1: Start heating only (no stirring)
            logger.info(f"Starting heating to {self.test_temperature}°C (no stirring)...")
            self.medusa.heat_stir(
                vessel=vessel,
                temperature=self.test_temperature,
                rpm=0
            )
            
            # Test 2: Monitor temperature
            logger.info("Monitoring temperature for 20 seconds...")
            start_time = time.time()
            temperatures = []
            
            while time.time() - start_time < 20:
                try:
                    temp = self.medusa.get_hotplate_temperature(vessel)
                    temperatures.append(temp)
                    logger.info(f"Current temperature: {temp}°C")
                    time.sleep(5)
                except Exception as e:
                    logger.warning(f"Could not read temperature: {e}")
                    break
            
            # Test 3: Test different temperature setpoints
            test_temps = [30, 40, 25]
            for temp in test_temps:
                logger.info(f"Testing temperature setpoint: {temp}°C")
                self.medusa.heat_stir(vessel=vessel, temperature=temp, rpm=0)
                time.sleep(8)
                
                try:
                    current_temp = self.medusa.get_hotplate_temperature(vessel)
                    logger.info(f"Temperature reached: {current_temp}°C")
                except Exception as e:
                    logger.warning(f"Could not read temperature: {e}")
            
            # Test 4: Stop heating
            logger.info("Stopping heating...")
            self.medusa.heat_stir(vessel=vessel, temperature=0, rpm=0)
            
            logger.info("Heat plate test completed")
            
            return {
                "success": True,
                "vessel": vessel,
                "test_temperatures": test_temps,
                "temperature_readings": temperatures,
                "monitoring_duration": 20,
                "tests_performed": [
                    "heating_only_startup",
                    "temperature_monitoring",
                    "multiple_temperature_setpoints",
                    "system_shutdown"
                ]
            }
            
        except Exception as e:
            logger.error(f"Heat plate test failed: {e}")
            return {"success": False, "error": str(e), "vessel": vessel}
    
    def test_stirring_only(self, vessel: str = "Reaction_Vial") -> Dict[str, Any]:
        """
        Test stirring functionality without heating.
        
        Args:
            vessel (str): Vessel to test
            
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info(f"Testing stirring only for {vessel}")
        
        if not self.user_confirmation(f"Proceed with stirring test for {vessel}?"):
            return {"success": False, "reason": "User cancelled"}
        
        if not self._check_medusa_initialized():
            return {"success": False, "error": "Medusa not initialized"}
        
        # Type assertion to help the type checker
        assert self.medusa is not None
        
        try:
            # Test 1: Start stirring only (no heating)
            logger.info(f"Starting stirring at {self.test_rpm} RPM (no heating)...")
            self.medusa.heat_stir(
                vessel=vessel,
                temperature=0,
                rpm=self.test_rpm
            )
            
            # Test 2: Monitor stirring for 15 seconds
            logger.info("Monitoring stirring for 15 seconds...")
            start_time = time.time()
            stirring_readings = []
            
            while time.time() - start_time < 15:
                try:
                    rpm = self.medusa.get_hotplate_rpm(vessel)
                    stirring_readings.append(rpm)
                    logger.info(f"Current RPM: {rpm}")
                except Exception as e:
                    logger.debug(f"Could not read RPM (method may not exist): {e}")
                    logger.info("Stirring is active...")
                time.sleep(3)
            
            # Test 3: Test different stirring speeds
            test_rpms = [150, 300, 50, 100]
            for rpm in test_rpms:
                logger.info(f"Testing stirring speed: {rpm} RPM")
                self.medusa.heat_stir(vessel=vessel, temperature=0, rpm=rpm)
                time.sleep(5)
                
                try:
                    current_rpm = self.medusa.get_hotplate_rpm(vessel)
                    logger.info(f"RPM reached: {current_rpm}")
                except Exception as e:
                    logger.debug(f"Could not read RPM (method may not exist): {e}")
                    logger.info(f"RPM set to: {rpm}")
            
            # Test 4: Stop stirring
            logger.info("Stopping stirring...")
            self.medusa.heat_stir(vessel=vessel, temperature=0, rpm=0)
            
            logger.info("Stirring test completed")
            
            return {
                "success": True,
                "vessel": vessel,
                "test_rpms": test_rpms,
                "stirring_readings": stirring_readings if stirring_readings else None,
                "monitoring_duration": 15,
                "tests_performed": [
                    "stirring_only_startup",
                    "rpm_monitoring",
                    "multiple_rpm_setpoints",
                    "system_shutdown"
                ]
            }
            
        except Exception as e:
            logger.error(f"Stirring test failed: {e}")
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
            
            # 2. Test heat plate only
            logger.info("Step 2: Testing heat plate only...")
            workflow_results["heat_plate_only"] = self.test_heat_plate_only()
            
            # 3. Test stirring only
            logger.info("Step 3: Testing stirring only...")
            workflow_results["stirring_only"] = self.test_stirring_only()
            
            # 4. Test linear actuator
            logger.info("Step 4: Testing linear actuator...")
            workflow_results["linear_actuator"] = self.test_linear_actuator()
            
            # 5. Test syringe pump
            logger.info("Step 5: Testing syringe pump...")
            workflow_results["syringe_pump"] = self.test_syringe_pump(
                "Solvent_Monomer_Modification_Pump",
                "Solvent_Vessel",
                "Waste_Vessel",
                volume=0.5
            )
            
            # 6. Test UV-VIS spectrometer
            logger.info("Step 6: Testing UV-VIS spectrometer...")
            workflow_results["uv_vis"] = self.test_uv_vis_spectrometer()
            
            # 7. Test solenoid valve
            logger.info("Step 7: Testing solenoid valve...")
            workflow_results["solenoid_valve"] = self.test_solenoid_valve()
            
            # 8. Test polymer peristaltic pump
            logger.info("Step 8: Testing polymer peristaltic pump...")
            workflow_results["polymer_peristaltic_pump"] = self.test_polymer_peristaltic_pump()
            
            # 9. Test solvent peristaltic pump
            logger.info("Step 9: Testing solvent peristaltic pump...")
            workflow_results["solvent_peristaltic_pump"] = self.test_solvent_peristaltic_pump()
            
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
        Run all individual device tests including enhanced heat plate and peristaltic pump tests.
        
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
            ("heat_plate_only", lambda: self.test_heat_plate_only()),
            ("stirring_only", lambda: self.test_stirring_only()),
            ("uv_vis_spectrometer", self.test_uv_vis_spectrometer),
            ("syringe_pump_solvent", lambda: self.test_syringe_pump("Solvent_Monomer_Modification_Pump", "Solvent_Vessel", "Waste_Vessel")),
            ("syringe_pump_initiator", lambda: self.test_syringe_pump("Initiator_CTA_Pump", "Initiator_Vessel", "Waste_Vessel")),
            ("polymer_peristaltic_pump", self.test_polymer_peristaltic_pump),
            ("solvent_peristaltic_pump", self.test_solvent_peristaltic_pump),
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
        print("   e) Heat plate only")
        print("   f) Stirring only")
        print("   g) UV-VIS spectrometer")
        print("   h) Syringe pump")
        print("   i) Peristaltic pump (generic)")
        print("   j) Polymer peristaltic pump")
        print("   k) Solvent peristaltic pump")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            results = controller.run_all_tests()
            print(f"\nAll tests completed: {results['successful_tests']}/{results['total_tests']} passed")
            
        elif choice == "2":
            results = controller.test_complete_workflow_simulation()
            print(f"\nWorkflow simulation completed: {results['successful_tests']}/{results['total_tests']} passed")
            
        elif choice == "3":
            device_choice = input("Select device (a-k): ").strip().lower()
            
            if device_choice == "a":
                controller.test_gas_valve()
            elif device_choice == "b":
                controller.test_solenoid_valve()
            elif device_choice == "c":
                controller.test_linear_actuator()
            elif device_choice == "d":
                controller.test_heating_stirring()
            elif device_choice == "e":
                controller.test_heat_plate_only()
            elif device_choice == "f":
                controller.test_stirring_only()
            elif device_choice == "g":
                controller.test_uv_vis_spectrometer()
            elif device_choice == "h":
                pump_id = input("Enter pump ID: ").strip()
                source = input("Enter source vessel: ").strip()
                target = input("Enter target vessel: ").strip()
                controller.test_syringe_pump(pump_id, source, target)
            elif device_choice == "i":
                pump_id = input("Enter pump ID: ").strip()
                source = input("Enter source vessel: ").strip()
                target = input("Enter target vessel: ").strip()
                controller.test_peristaltic_pump(pump_id, source, target)
            elif device_choice == "j":
                controller.test_polymer_peristaltic_pump()
            elif device_choice == "k":
                controller.test_solvent_peristaltic_pump()
            else:
                print("Invalid device choice.")
                
        elif choice == "4":
            print("Exiting device test controller.")
            break
            
        else:
            print("Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    main() 