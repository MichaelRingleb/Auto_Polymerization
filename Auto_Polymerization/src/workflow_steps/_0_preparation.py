"""
_0_preparation.py

Preparation module for the Auto_Polymerization workflow.
Encapsulates all steps required to prepare the system before polymerization, including NMR shimming, vial handling, heatplate preheating, gas valve control, and tubing priming.

All user-editable settings (draw_speeds, dispense_speeds, volumes, temperatures, etc.) should be set in users/config/platform_config.py and supplied as arguments from the controller.

All priming and analytical transfers now use serial_communication_error_safe_transfer_volumetric, a direct, parameter-preserving,
error-safe wrapper for medusa.transfer_volumetric. All transfer parameters (source, target, pump_id, transfer_type, volume, etc.)
are passed through unchanged. The only difference is robust retry logic for COM port conflicts.

Supported keys for draw_speeds and dispense_speeds include: 'solvent', 'monomer', 'initiator', 'cta', 'modification', 'nmr', 'uv_vis'.

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
"""
import time
from serial.serialutil import SerialException
from src.liquid_transfers.liquid_transfers_utils import (
    serial_communication_error_safe_transfer_volumetric,
    to_nmr_liquid_transfer_shimming,
    from_nmr_liquid_transfer_shimming,
)
import importlib.util
import sys
import os

# All calls to serial_communication_error_safe_transfer_volumetric now use the imported version.
# Update any docstrings/comments to note the function is imported from liquid_transfers_utils.


def shim_nmr_sample(medusa, shim_level=2, shim_repeats=2):
    """
    Transfer deuterated solvent to NMR, perform shimming, and return solvent to the original vessel.
    Uses modular analytical transfer functions for shimming.
    Args:
        medusa: Medusa instance for liquid handling
        shim_level: Shimming level (default 2)
        shim_repeats: Number of shimming repetitions (default 2)
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
    Args:
        medusa: Medusa instance
        polymerization_temp: Target temperature for polymerization
        set_rpm: Stirring speed (rpm)
    """
    medusa.logger.info("Moving reaction vial out of heatplate...")
    medusa.write_serial("Linear_Actuator", "2000")
    medusa.logger.info(f"Preheating heatplate to {polymerization_temp}°C and setting RPM to {set_rpm}...")
    medusa.heat_stir(vessel="Reaction_Vial", temperature=polymerization_temp, rpm=set_rpm)


def open_gas_valve(medusa):
    """
    Open the gas valve (default mode: gas flow blocked).
    Args:
        medusa: Medusa instance
    """
    medusa.logger.info("Opening gas valve...")
    medusa.write_serial("Gas_Valve", "GAS_ON")


def prime_tubing(medusa, prime_transfer_params):
    """
    Prime tubing from each vessel to waste using the appropriate pumps.
    All priming steps now use serial_communication_error_safe_transfer_volumetric, a direct, parameter-preserving,
    error-safe wrapper for medusa.transfer_volumetric. All transfer parameters are passed through unchanged.
    The only difference is robust retry logic for COM port conflicts (PermissionError).
    Args:
        medusa: Medusa instance
        prime_transfer_params: dict containing all transfer parameters for all priming steps
    """
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "Solvent_Vessel", "target": "Waste_Vessel", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1)
    })
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "Monomer_Vessel", "target": "Waste_Vessel", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1)
    })
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "Initiator_Vessel", "target": "Waste_Vessel", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1)
    })
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "CTA_Vessel", "target": "Waste_Vessel", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1)
    })
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "Modification_Vessel", "target": "Waste_Vessel", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1)
    })


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
    import threading
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