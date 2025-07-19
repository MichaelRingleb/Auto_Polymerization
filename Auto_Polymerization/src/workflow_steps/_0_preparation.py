"""
_0_preparation.py

Preparation module for the Auto_Polymerization workflow.
Encapsulates all steps required to prepare the system before polymerization, including NMR shimming, vial handling, heatplate preheating, gas valve control, and tubing priming.

All user-editable settings (draw_speeds, dispense_speeds, volumes, temperatures, etc.) should be set in users/config/platform_config.py and supplied as arguments from the controller.

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

def retry_on_com_error(func, max_retries=3, initial_delay=120, max_delay=300):
    """
    Retry a function that might fail due to COM port errors.
    
    This function implements exponential backoff for COM port permission errors that can
    occur when multiple threads try to access the same serial port simultaneously.
    This is particularly useful for syringe pumps that share a COM port but have
    different addresses.
    
    Args:
        func: Function to retry (should be a callable that might raise SerialException)
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 120 = 2 minutes)
        max_delay: Maximum delay in seconds (default: 300 = 5 minutes)
    
    Returns:
        The result of func() if successful
        
    Raises:
        SerialException: If the function fails after all retry attempts, or if the error
                        is not a COM port permission error
        
    Example:
        def my_transfer():
            return medusa.transfer_volumetric(...)
        
        result = retry_on_com_error(my_transfer)
    """
    for attempt in range(max_retries + 1):  # +1 for the initial attempt
        try:
            if attempt == 0:
                print(f"Attempting transfer (initial attempt)...")
            else:
                print(f"Attempting transfer (retry {attempt}/{max_retries})...")
            
            result = func()
            
            if attempt == 0:
                print(f"Transfer completed successfully on first attempt!")
            else:
                print(f"Transfer completed successfully on retry {attempt}!")
            
            return result
            
        except SerialException as e:
            # Only retry COM port permission errors, not other serial issues
            if "PermissionError" in str(e) and "COM" in str(e):
                if attempt < max_retries:
                    # Exponential backoff: delay doubles each retry, capped at max_delay
                    delay = min(initial_delay * (2 ** attempt), max_delay)
                    print(f"❌ COM port error on attempt {attempt + 1}: {e}")
                    print(f"⏳ Waiting {delay} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"❌ Failed after {max_retries + 1} attempts. Last error: {e}")
                    print(f"💡 This might indicate a hardware issue or persistent COM port conflict.")
                    raise
            else:
                # Re-raise immediately if it's not a COM port permission error
                print(f"❌ Non-COM port serial error: {e}")
                raise

def safe_transfer_volumetric(medusa, **kwargs):
    """
    Wrapper for medusa.transfer_volumetric with COM port retry logic.
    
    This function wraps medusa.transfer_volumetric calls with retry logic to handle
    COM port conflicts that can occur during parallel execution of preparation steps.
    It automatically retries failed transfers with exponential backoff.
    
    Args:
        medusa: Medusa instance for liquid handling
        **kwargs: All arguments to pass to medusa.transfer_volumetric
        
    Returns:
        The result of medusa.transfer_volumetric if successful
        
    Raises:
        SerialException: If the transfer fails after all retry attempts
        
    Example:
        # Instead of:
        # medusa.transfer_volumetric(source="A", target="B", volume=5)
        
        # Use:
        safe_transfer_volumetric(medusa, source="A", target="B", volume=5)
    """
    # Log the transfer details for debugging
    source = kwargs.get('source', 'Unknown')
    target = kwargs.get('target', 'Unknown')
    volume = kwargs.get('volume', 'Unknown')
    pump_id = kwargs.get('pump_id', 'Unknown')
    print(f"🔄 Starting transfer: {volume}mL from {source} to {target} via {pump_id}")
    
    def transfer_func():
        return medusa.transfer_volumetric(**kwargs)
    
    return retry_on_com_error(transfer_func)

# Example usage:
# from users.config import platform_config as config
# draw_speeds = config.draw_speeds
# dispense_speeds = config.dispense_speeds
# polymerization_temp = config.polymerization_temp
# set_rpm = config.set_rpm

# All transfer calls use .get() for draw_speeds and dispense_speeds, so new keys are supported automatically.
# If you add new components to the config, ensure to use the same keys in your workflow logic.


def shim_nmr_sample(medusa, volume=2.1, pump_id="Analytical_Pump", source="Deuterated_Solvent", target="NMR", shim_level=2, shim_repeats=2, draw_speed=0.2, dispense_speed=0.2):
    """
    Transfer deuterated solvent to NMR, perform shimming, and return solvent to the original vessel.
    
    This function uses safe_transfer_volumetric to handle potential COM port conflicts
    during the NMR shimming process, which runs in parallel with other preparation steps.
    
    Args:
        medusa: Medusa instance for liquid handling
        volume: Volume to transfer (default 3)
        pump_id: Pump to use (default 'Analytical_Pump')
        source: Source vessel (default 'Deuterated_Solvent')
        target: Target vessel (default 'NMR')
        shim_level: Shimming level (default 2)
        shim_repeats: Number of shimming repetitions (default 2)
        draw_speed: Syringe draw speed (from config or controller)
        dispense_speed: Syringe dispense speed (from config or controller)
    """
    import src.NMR.nmr_utils as nmr
    medusa.logger.info("Transferring deuterated solvent to NMR for shimming...")
    # Use safe_transfer_volumetric to handle COM port conflicts
    safe_transfer_volumetric(medusa, source=source, target=target, pump_id=pump_id, 
                             volume=volume, transfer_type="liquid", draw_speed=draw_speed, dispense_speed=dispense_speed)
    for _ in range(shim_repeats):
        nmr.run_shimming(shim_level)
        medusa.logger.info(f"NMR shimming (level {shim_level}) complete.")
    medusa.logger.info("Transferring solvent back to deuterated solvent vessel...")
    # Use safe_transfer_volumetric to handle potential COM port conflicts for the syringe pumps
    safe_transfer_volumetric(medusa, source=target, target=source, pump_id=pump_id, 
                             volume=(volume), transfer_type="liquid", draw_speed=draw_speed, dispense_speed=dispense_speed, 
                             post_rinse_vessel = "Purge_Solvent_Vessel_2", post_rinse = 1, post_rinse_speed = 0.3)


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


def prime_tubing(medusa, volume=2, draw_speeds=None, dispense_speeds=None):
    """
    Prime tubing from each vessel to waste using the appropriate pumps.
    
    This function performs multiple sequential transfers to prime the tubing from
    different vessels. Each transfer uses safe_transfer_volumetric to handle potential
    COM port conflicts that can occur when this function runs in parallel with
    NMR shimming (both using syringe pumps on the same COM port).
    
    Args:
        medusa: Medusa instance
        volume: Volume to prime from each vessel (default 3)
        draw_speeds: dict mapping component names to draw speeds (must be supplied by caller)
        dispense_speeds: dict mapping component names to dispense speeds (must be supplied by caller)
    Notes:
        Uses .get() for each component, so missing keys will use a default value of 3.
        Adds flush=1 to each transfer for effective priming.
        All transfers use safe_transfer_volumetric with retry logic for COM port errors.
        The retry mechanism ensures that if COM port conflicts occur (e.g., with NMR shimming),
        the transfers will automatically wait and retry with exponential backoff.
    """
    if draw_speeds is None:
        draw_speeds = {}
    if dispense_speeds is None:
        dispense_speeds = {}
    medusa.logger.info("Priming tubing from solvent, monomer, modification, initiator, and CTA vessels to waste...")
    
    # Use safe_transfer_volumetric for all transfers with retry logic
    # This handles COM port conflicts that can occur when running in parallel with NMR shimming
    safe_transfer_volumetric(medusa, source="Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", 
                             volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("solvent", 0.133), dispense_speed=dispense_speeds.get("solvent", 0.1),
                             flush=1, 
                             post_rinse_vessel = "Purge_Solvent_Vessel_1", post_rinse = 1, post_rinse_speed = 0.3)
    safe_transfer_volumetric(medusa, source="Monomer_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump",
                             volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("monomer", 0.1), dispense_speed=dispense_speeds.get("monomer", 0.1), 
                             flush=1, 
                             post_rinse = 1, post_rinse_speed = 0.3)
    safe_transfer_volumetric(medusa, source="Modification_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", 
                             volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("modification", 0.05), dispense_speed=dispense_speeds.get("modification", 0.1), 
                             flush=1, 
                             post_rinse_vessel = "Purge_Solvent_Vessel_1",post_rinse = 1, post_rinse_speed = 0.3)
    safe_transfer_volumetric(medusa, source="Initiator_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", 
                             volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("initiator", 0.5), dispense_speed=dispense_speeds.get("initiator", 0.1), 
                             flush=1, 
                             post_rinse_vessel = "Purge_Solvent_Vessel_1",post_rinse = 1, post_rinse_speed = 0.3)
    safe_transfer_volumetric(medusa, source="CTA_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", 
                             volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("cta", 0.5), dispense_speed=dispense_speeds.get("cta", 0.1), 
                             flush=1, 
                             post_rinse_vessel = "Purge_Solvent_Vessel_1",post_rinse = 1, post_rinse_speed = 0.3)


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
    prime_volume=2,
    run_minimal_test=False,
    draw_speeds=None,
    dispense_speeds=None
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
    calls use safe_transfer_volumetric with retry logic.
    
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
        - safe_transfer_volumetric handles conflicts with automatic retry
        - No manual synchronization needed - the retry logic handles it automatically
    """
    import threading
    if run_minimal_test:
        from Auto_Polymerization.tests.test_minimal_workflow import run_minimal_workflow_test
        run_minimal_workflow_test(medusa)

    if shim_kwargs is None:
        shim_kwargs = {}
    if draw_speeds is None:
        draw_speeds = {}
    if dispense_speeds is None:
        dispense_speeds = {}

    # Define the two subworkflows as functions
    def nmr_shim_workflow():
        # Use draw_speeds and dispense_speeds for NMR shimming if provided
        # This workflow uses safe_transfer_volumetric internally to handle COM port conflicts
        shim_nmr_sample(
            medusa,
            draw_speed=draw_speeds.get("nmr", 0.1),
            dispense_speed=dispense_speeds.get("nmr", 0.1),
            **shim_kwargs
        )

    def other_prep_workflow():
        # This workflow uses safe_transfer_volumetric internally to handle COM port conflicts
        prepare_reaction_vial_and_heatplate(medusa, polymerization_temp, set_rpm)
        open_gas_valve(medusa)
        prime_tubing(medusa, volume=prime_volume, draw_speeds=draw_speeds, dispense_speeds=dispense_speeds)
        close_gas_valve(medusa)

    # Create threads for parallel execution
    # Both threads may use syringe pumps on the same COM port, but safe_transfer_volumetric
    # handles any conflicts with automatic retry logic
    t1 = threading.Thread(target=nmr_shim_workflow)
    t2 = threading.Thread(target=other_prep_workflow)

    # Start both threads
    t1.start()
    t2.start()

    # Wait for both to finish
    t1.join()
    t2.join() 