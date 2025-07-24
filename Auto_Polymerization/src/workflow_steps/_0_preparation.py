"""
Auto_Polymerization Preparation Module

This module handles all preparation steps required before polymerization, including:
- NMR shimming with deuterated solvent
- Reaction vial positioning and heatplate preheating
- Gas valve control for deoxygenation
- System tubing priming and cleaning
- Hardware initialization and setup

Key Features:
- Parallel NMR shimming and preparation workflows
- Error-safe liquid transfers with COM port conflict handling
- Configurable parameters for all operations
- Comprehensive logging and error reporting
- Modular design for easy testing and maintenance

All user-editable settings (draw_speeds, dispense_speeds, volumes, temperatures, etc.) 
should be set in users/config/platform_config.py and supplied as arguments from the controller.

All priming and analytical transfers use serial_communication_error_safe_transfer_volumetric, 
a direct, parameter-preserving, error-safe wrapper for medusa.transfer_volumetric. 
All transfer parameters are passed through unchanged. The only difference is robust 
retry logic for COM port conflicts.

Supported keys for draw_speeds and dispense_speeds include: 
'solvent', 'monomer', 'initiator', 'cta', 'modification', 'nmr', 'uv_vis'.

All functions are designed to be called from a workflow controller script.

COM PORT RETRY LOGIC:
This module includes robust error handling for COM port conflicts that can occur when multiple
threads try to access the same serial port simultaneously. This is particularly important for
syringe pumps that share the same COM port but have different addresses.

The retry mechanism:
- Catches SerialException with PermissionError for COM ports
- Implements exponential backoff (2 minutes, 4 minutes, 5 minutes max)
- Retries up to 3 times before giving up
- Only retries COM port permission errors, not other serial issues
- Provides clear logging of retry attempts and delays

This approach allows the parallel preparation workflow (NMR shimming + other prep steps) to
run without COM port conflicts, automatically waiting for transfers to complete before retrying.

Dependencies:
- medusa: Hardware control framework
- src.liquid_transfers.liquid_transfers_utils: Error-safe transfer functions
- src.NMR.nmr_utils: NMR shimming and analysis utilities
- users.config.platform_config: Configuration parameters

Author: Michael Ringleb (with help from cursor.ai)
Date: [Current Date]
Version: 1.0
"""

import time
from serial.serialutil import SerialException
from src.liquid_transfers.liquid_transfers_utils import (
    serial_communication_error_safe_transfer_volumetric,
    to_nmr_liquid_transfer_shimming,
    from_nmr_liquid_transfer_shimming, prime_tubing
)
import importlib.util
import sys
import os
import threading
import users.config.platform_config as config


def shim_nmr_sample(medusa, shim_level=2, shim_repeats=2):
    """
    Transfer deuterated solvent to NMR, perform shimming, and return solvent to the original vessel.
    
    This function performs NMR shimming to optimize magnetic field homogeneity for high-quality
    NMR spectra. It transfers deuterated solvent (typically DMSO-d6) to the NMR spectrometer,
    performs shimming at the specified level, then returns the solvent to preserve the expensive
    deuterated material.
    
    Args:
        medusa: Medusa instance for hardware control
        shim_level (int): Shimming level (default: 2)
        shim_repeats (int): Number of shimming repetitions (default: 2)
        
    Returns:
        None: Shimming operations are performed via hardware control
    """
    import src.NMR.nmr_utils as nmr
    medusa.logger.info("Transferring deuterated solvent to NMR for shimming...")
    to_nmr_liquid_transfer_shimming(medusa)
    for _ in range(shim_repeats):
        nmr.run_shimming(shim_level)
        medusa.logger.info(f"NMR shimming (level {shim_level}) complete.")
    medusa.logger.info("Transferring solvent back to deuterated solvent vessel...")
    from_nmr_liquid_transfer_shimming(medusa)


def prepare_reaction_vial_and_heatplate(medusa, polymerization_temp, set_rpm):
    """
    Move the reaction vial out of the heatplate and preheat the heatplate.
    
    This function positions the reaction vial for component addition and preheats
    the heatplate to the target polymerization temperature. The vial is moved out
    of the heatplate to allow for safe component addition, then the heatplate is
    preheated to minimize temperature equilibration time during polymerization.
    
    Args:
        medusa: Medusa instance for hardware control
        polymerization_temp (float): Target temperature for polymerization (°C)
        set_rpm (int): Stirring speed for the reaction (rpm)
        
    Returns:
        None: Hardware operations are performed via Medusa control
    """
    medusa.logger.info("Moving reaction vial out of heatplate...")
    medusa.write_serial("Linear_Actuator", "2000")
    medusa.logger.info(f"Preheating heatplate to {polymerization_temp}°C and setting RPM to {set_rpm}...")
    medusa.heat_stir(vessel="Reaction_Vial", temperature=polymerization_temp, rpm=set_rpm)


def open_gas_valve(medusa):
    """
    Open the gas valve for deoxygenation operations.
    
    This function opens the gas valve to allow argon flow for deoxygenation
    of the reaction mixture. The valve is typically in a closed state by default
    to prevent unwanted gas flow.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Valve operation is performed via serial communication
    """
    medusa.logger.info("Opening gas valve...")
    medusa.write_serial("Gas_Valve", "GAS_ON")





def close_gas_valve(medusa):
    """
    Close the gas valve.
    Args:
        medusa: Medusa instance
    """
    medusa.logger.info("Closing gas valve...")
    medusa.write_serial("Gas_Valve", "GAS_OFF")


def run_preparation_workflow(
    medusa,
    polymerization_temp,
    set_rpm,
    shim_kwargs=None,
    run_minimal_test=False,
    prime_transfer_params=None,
   
):
    """
    Execute the full preparation workflow in parallel:
    - NMR shimming (solvent transfer, shimming, return)
    - All other steps (vial/heatplate, gas valve, priming)
    Both must finish before returning.

    Optionally runs the minimal workflow test at the start if run_minimal_test is True.

    PARALLEL EXECUTION AND COM PORT HANDLING:
    This function runs NMR shimming and other preparation steps in parallel using threading.
    Both workflows use syringe pumps that may share the same COM port (e.g., COM7) but with
    different addresses. To handle potential COM port conflicts, all transfer_volumetric
    calls use serial_communication_error_safe_transfer_volumetric with retry logic.
    
    The retry mechanism ensures that if one thread is using the COM port, the other thread
    will automatically wait and retry with exponential backoff (2 min, 4 min, 5 min max),
    rather than crashing with a PermissionError.

    Args:
        medusa: Medusa instance
        polymerization_temp: Target temperature for polymerization
        set_rpm: Stirring speed (rpm)
        shim_kwargs: Optional dict of keyword arguments for shim_nmr_sample
        prime_volume: Volume to use for priming (default 3)
        run_minimal_test: If True, runs the minimal workflow test before preparation
        draw_speeds: dict mapping component names to draw speeds (must be supplied by caller)
        dispense_speeds: dict mapping component names to dispense speeds (must be supplied by caller)
    Notes:
    This function orchestrates the preparation phase of the polymerization reaction.
    It includes shimming the NMR spectrometer with deuterated solvent, removing the reaction vial from the heatplate, preheating the heatplate, 
        and priming the tubings from the reaction component stock vials to the pumps.
    The minimal workflow test gives the user the chance to check the hardware before the actual workflow starts.
        All steps are executed in parallel using threading and both must finish before returning.
        
        COM PORT CONFLICT RESOLUTION:
        - NMR shimming and tubing priming run in parallel
        - Both use syringe pumps that may share the same COM port
        - serial_communication_error_safe_transfer_volumetric handles conflicts with automatic retry
        - No manual synchronization needed - the retry logic handles it automatically
    """

    if run_minimal_test:
        # Dynamically import test_minimal_workflow from the correct path
        test_path = os.path.join(os.path.dirname(__file__), '../../tests/test_minimal_workflow.py')
        test_path = os.path.abspath(test_path)
        spec = importlib.util.spec_from_file_location("test_minimal_workflow", test_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load test_minimal_workflow module from {test_path}")
        test_module = importlib.util.module_from_spec(spec)
        sys.modules["test_minimal_workflow"] = test_module
        spec.loader.exec_module(test_module)
        test_module.run_minimal_workflow_test(medusa)

    if shim_kwargs is None:
        shim_kwargs = {}

    # Define the two subworkflows as functions
    def nmr_shim_workflow():
        # Use draw_speeds and dispense_speeds for NMR shimming if provided
        # This workflow uses serial_communication_error_safe_transfer_volumetric internally to handle COM port conflicts
        shim_nmr_sample(
            medusa,
            **shim_kwargs
        )

    def other_prep_workflow():
        # This workflow uses serial_communication_error_safe_transfer_volumetric internally to handle COM port conflicts
        prepare_reaction_vial_and_heatplate(medusa, polymerization_temp, set_rpm)
        open_gas_valve(medusa)
        prime_tubing(medusa, prime_transfer_params)
        close_gas_valve(medusa)

    # Create threads for parallel execution
    # Both threads may use syringe pumps on the same COM port, but serial_communication_error_safe_transfer_volumetric
    # handles any conflicts with automatic retry logic
    t1 = threading.Thread(target=nmr_shim_workflow)
    t2 = threading.Thread(target=other_prep_workflow)

    # Start both threads
    t1.start()
    t2.start()

    # Wait for both to finish
    t1.join()
    t2.join() 