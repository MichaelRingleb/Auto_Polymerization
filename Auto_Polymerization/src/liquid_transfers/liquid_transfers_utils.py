"""
Auto_Polymerization Liquid Transfer Utilities

This module provides robust and modular liquid transfer functions for the Auto_Polymerization platform.
It includes error-safe wrappers for all hardware transfers and specialized functions for different
workflow steps.

Key Features:
- Error-safe transfer functions with COM port conflict handling
- Specialized transfer functions for UV-VIS, NMR, and modification workflows
- Config-driven parameters for all transfer operations
- Exponential backoff retry logic for serial communication errors
- Comprehensive logging and error reporting

Core Functions:
- serial_communication_error_safe_transfer_volumetric: Main error-safe wrapper
- retry_on_serial_com_error: Retry logic with exponential backoff
- UV-VIS transfers: Reference, sampling, and cleanup operations
- NMR transfers: Shimming and sampling operations
- Modification transfers: Reagent addition with full parameter support
- Deoxygenation: Active gas pumping for reaction mixture deoxygenation

All transfer functions use the error-safe wrapper to ensure robust operation
in multithreaded environments where COM port conflicts may occur.

Dependencies:
- medusa: Hardware control framework
- users.config.platform_config: Configuration parameters
- serial.serialutil: Serial communication error handling

Author: Michael Ringleb (with help from cursor.ai)
Date: [Current Date]
Version: 1.0
"""

import time
from serial.serialutil import SerialException
from users.config import platform_config as config


def retry_on_serial_com_error(func, max_retries=3, initial_delay=120, max_delay=300, logger=None):
    """
    Retry a function that might fail due to COM port errors with exponential backoff.
    
    This function implements intelligent retry logic specifically for COM port permission
    errors that can occur in multithreaded environments. It uses exponential backoff
    to avoid overwhelming the system while providing clear logging of retry attempts.
    
    Args:
        func (callable): Function to retry
        max_retries (int): Maximum number of retry attempts (default: 3)
        initial_delay (int): Initial delay in seconds (default: 120)
        max_delay (int): Maximum delay in seconds (default: 300)
        logger (logging.Logger, optional): Logger instance for messages
        
    Returns:
        Any: Return value from the successful function call
        
    Raises:
        SerialException: If all retry attempts fail or for non-COM port errors
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except SerialException as e:
            if "PermissionError" in str(e) and "COM" in str(e):
                if attempt < max_retries:
                    delay = min(initial_delay * (2 ** attempt), max_delay)
                    msg1 = f"❌ COM port error on attempt {attempt + 1}: {e}"
                    msg2 = f"⏳ Waiting {delay} seconds before retry {attempt + 1}/{max_retries}..."
                    if logger:
                        logger.error(msg1)
                        logger.info(msg2)
                    else:
                        print(msg1)
                        print(msg2)
                    time.sleep(delay)
                    continue
                else:
                    msg1 = f"❌ Failed after {max_retries + 1} attempts. Last error: {e}"
                    msg2 = f"💡 This might indicate a hardware issue or persistent COM port conflict."
                    if logger:
                        logger.error(msg1)
                        logger.warning(msg2)
                    else:
                        print(msg1)
                        print(msg2)
                    raise
            else:
                msg = f"❌ Non-COM port serial error: {e}"
                if logger:
                    logger.error(msg)
                else:
                    print(msg)
                raise


def serial_communication_error_safe_transfer_volumetric(medusa, logger=None, **kwargs):
    """
    Direct, parameter-preserving, error-safe wrapper for medusa.transfer_volumetric.
    
    This function wraps medusa.transfer_volumetric with robust error handling for
    COM port conflicts. All parameters are passed through unchanged, ensuring that
    no transfer logic or parameter names are altered. The only difference is the
    addition of retry logic for serial communication errors.
    
    Args:
        medusa: Medusa instance for hardware control
        logger (logging.Logger, optional): Logger instance for error messages
        **kwargs: All parameters to pass to medusa.transfer_volumetric
        
    Returns:
        Any: Return value from medusa.transfer_volumetric
        
    Raises:
        SerialException: If all retry attempts fail
    """
    def transfer_func():
        return medusa.transfer_volumetric(**kwargs)
    return retry_on_serial_com_error(transfer_func, logger=logger)



def prime_tubing(medusa, prime_transfer_params):
    """
    Prime tubing from each vessel to waste using the appropriate pumps.
    
    This function performs comprehensive tubing priming to ensure all fluid paths
    are properly filled and free of air bubbles. It primes each pump path from
    its source vessel to waste, using configurable parameters for volumes, speeds,
    and flush operations.
    
    All priming steps use serial_communication_error_safe_transfer_volumetric for
    robust error handling of COM port conflicts.
    
    Args:
        medusa: Medusa instance for hardware control
        prime_transfer_params (dict): Dictionary containing all transfer parameters
            for priming operations including volumes, speeds, flush settings, etc.
            
    Returns:
        None: Priming operations are performed via error-safe transfer functions
    """
    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Solvent_Vessel", "target": "Waste_Vessel", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1)    
    })

    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Monomer_Vessel", "target": "Waste_Vessel", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1)
    })

    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Initiator_Vessel", "target": "Waste_Vessel", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1)
    })

    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "CTA_Vessel", "target": "Waste_Vessel", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1)
    })

    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Modification_Vessel", "target": "Waste_Vessel", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": prime_transfer_params.get("transfer_type", "liquid"),
        "pre_rinse": prime_transfer_params.get("pre_rinse", 1), "pre_rinse_volume": prime_transfer_params.get("pre_rinse_volume", 1.0), "pre_rinse_speed": prime_transfer_params.get("pre_rinse_speed", 0.1),
        "volume": prime_transfer_params.get("prime_volume", 1.0), "draw_speed": prime_transfer_params.get("draw_speed", 0.1), "dispense_speed": prime_transfer_params.get("dispense_speed", 0.1),
        "flush": prime_transfer_params.get("flush", 1), "flush_volume": prime_transfer_params.get("flush_volume", 5), "flush_speed": prime_transfer_params.get("flush_speed", 0.1),
        "post_rinse_vessel": prime_transfer_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": prime_transfer_params.get("post_rinse", 1), "post_rinse_volume": prime_transfer_params.get("post_rinse_volume", 2.5),
        "post_rinse_speed": prime_transfer_params.get("post_rinse_speed", 0.1)        
    })




def add_modification_reagent_transfer(medusa):
    """
    Transfer modification reagent to reaction vial using error-safe transfer.
    
    This function transfers modification reagent (e.g., functionalization agent)
    from the modification vessel to the reaction vial. It includes comprehensive
    pre-rinse, post-rinse, and flush operations to ensure complete delivery
    and proper cleaning of the transfer path.
    
    All parameters are taken directly from config.modification_params to ensure
    consistency and ease of configuration.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    modification_params = config.modification_params
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="Modification_Vessel", target="Reaction_Vial", pump_id="Functionalization_Pump", 
        transfer_type="liquid", 
        volume=modification_params.get("modification_volume", 2), draw_speed=modification_params.get("modification_draw_speed", 0.08), dispense_speed=modification_params.get("modification_dispense_speed", 0.13),
        flush=modification_params.get("modification_flush", 1), flush_volume=modification_params.get("modification_flush_volume", 5), flush_speed=modification_params.get("modification_flush_speed", 0.15),
        pre_rinse=modification_params.get("pre_rinse", 1), pre_rinse_volume=modification_params.get("pre_rinse_volume", 0.7), pre_rinse_speed=modification_params.get("pre_rinse_speed", 0.1),
        post_rinse_vessel=modification_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), post_rinse=modification_params.get("post_rinse", 1), post_rinse_volume=modification_params.get("post_rinse_volume", 2.5),
        post_rinse_speed=modification_params.get("post_rinse_speed", 0.133),
        
    )


def deoxygenate_reaction_mixture(medusa, deoxygenation_time_sec, pump_id="Solvent_Monomer_Modification_Pump"):
    """
    Deoxygenate the reaction mixture using argon gas with active pumping.
    
    This function performs active deoxygenation by pumping argon gas through
    the reaction mixture in regular intervals. It opens the gas valve, pumps
    gas through the system in 1-second intervals for the specified duration,
    then closes the valve. This ensures thorough removal of oxygen from the
    reaction mixture before polymerization or modification reactions.
    
    Args:
        medusa: Medusa instance for hardware control
        deoxygenation_time_sec (int): Duration of deoxygenation in seconds
        pump_id (str): ID of the pump to use for deoxygenation (default: Solvent_Monomer_Modification_Pump)
        
    Returns:
        bool: True if successful, False otherwise
        
    Raises:
        Exception: If deoxygenation fails, with automatic valve cleanup
    """
    try:
        medusa.logger.info(f"Starting deoxygenation for {deoxygenation_time_sec} seconds using pump {pump_id}...")
        
        # Open gas valve
        medusa.write_serial("Gas_Valve", "GAS_ON")
        
        # Active deoxygenation: pump gas through system in intervals
        start_time = time.time()
        while time.time() - start_time < deoxygenation_time_sec:
            serial_communication_error_safe_transfer_volumetric(
                medusa,
                source="Gas_Reservoir_Vessel", 
                target="Reaction_Vial", 
                pump_id=pump_id, 
                volume=10, draw_speed=0.25, dispense_speed=0.1,
                transfer_type="gas", 
                flush=1, flush_speed=0.25, flush_volume=10,
                
            )
            time.sleep(1)  # 1-second intervals
        
        # Close gas valve
        medusa.write_serial("Gas_Valve", "GAS_OFF")
        
        medusa.logger.info("Deoxygenation completed successfully")
        return True
        
    except Exception as e:
        medusa.logger.error(f"Deoxygenation failed: {str(e)}")
        try:
            medusa.write_serial("Gas_Valve", "GAS_OFF")
        except:
            pass
        return False





def to_uv_vis_reference_transfer(medusa):
    """
    Transfer NMR solvent to UV-VIS cell for reference spectrum acquisition.
    
    This function transfers pure NMR solvent (typically deuterated DMSO) to the
    UV-VIS cell to establish a reference baseline for absorbance measurements.
    The reference spectrum is used to calculate absorbance values for reaction samples.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.uv_vis_transfer_params
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="NMR_Solvent_Vessel", 
        target="UV_VIS", 
        pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("volume", 1.5), draw_speed=params.get("draw_speed", 0.03), dispense_speed=params.get("dispense_speed", 0.016),
        post_rinse_vessel=params.get("post_rinse_vessel", "Purge_Solvent_Vessel_2"), post_rinse=params.get("post_rinse", 1), post_rinse_volume=params.get("post_rinse_volume", 1.5),
        post_rinse_speed=params.get("post_rinse_speed", 0.1)
    )


def to_uv_vis_sampling_transfer(medusa):
    """
    Transfer reaction mixture to UV-VIS cell for absorbance measurement.
    
    This function transfers reaction mixture from the reaction vial to the UV-VIS
    cell for absorbance spectrum acquisition. It's used for both t0 measurements
    and during reaction monitoring to track conversion progress.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.uv_vis_transfer_params
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="Reaction_Vial", target="UV_VIS", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("volume", 1.5), draw_speed=params.get("draw_speed", 0.03), dispense_speed=params.get("dispense_speed", 0.016), 
        post_rinse_vessel=params.get("post_rinse_vessel", "Purge_Solvent_Vessel_2"), post_rinse=params.get("post_rinse", 1), post_rinse_volume=params.get("post_rinse_volume", 1.5), 
        post_rinse_speed=params.get("post_rinse_speed", 0.1)
        
    )


def from_uv_vis_cleanup_transfer(medusa, target="NMR_Solvent_Vessel", volume=None):
    """
    Remove liquid from UV-VIS cell and transfer to target vessel.
    
    This function removes liquid from the UV-VIS cell after measurements and
    transfers it to a specified target vessel. It's used for cleaning the cell
    between different sample types (e.g., removing reference solvent before
    adding reaction mixture).
    
    Args:
        medusa: Medusa instance for hardware control
        target (str): Target vessel for the removed liquid (default: NMR_Solvent_Vessel)
        volume (float, optional): Volume to transfer (default: from config)
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.uv_vis_transfer_params
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="UV_VIS", target=target, pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("volume", 0.7), 
        draw_speed=params.get("draw_speed", 0.03), 
        dispense_speed=params.get("dispense_speed", 0.05),
        flush=params.get("flush", 1), 
        flush_volume=params.get("flush_volume", 2), 
        flush_speed=params.get("flush_speed", 0.05)
    )


def to_nmr_liquid_transfer_shimming(medusa):
    """
    Transfer deuterated solvent to NMR for shimming operations.
    
    This function transfers deuterated solvent (typically DMSO-d6) to the NMR
    spectrometer for shimming operations. Shimming is performed to optimize
    the magnetic field homogeneity for high-quality NMR spectra.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.nmr_transfer_params["shimming"]
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="Deuterated_Solvent", target="NMR", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("volume", 2.1), draw_speed=params.get("draw_speed", 0.05), dispense_speed=params.get("dispense_speed", 0.05),
        post_rinse_vessel=params.get("post_rinse_vessel", "Purge_Solvent_Vessel_2"), post_rinse=params.get("post_rinse", 1), post_rinse_volume=params.get("post_rinse_volume", 1.5),
        post_rinse_speed=params.get("post_rinse_speed", 0.1),
        
    )


def from_nmr_liquid_transfer_shimming(medusa):
    """
    Transfer deuterated solvent from NMR back to storage vessel after shimming.
    
    This function returns the deuterated solvent used for shimming back to its
    storage vessel. It's called after NMR shimming operations are complete to
    preserve the expensive deuterated solvent.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.nmr_transfer_params["shimming"]
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="NMR", target="Deuterated_Solvent", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("volume", 2.1), draw_speed=params.get("draw_speed", 0.05), dispense_speed=params.get("dispense_speed", 0.05),
        flush=params.get("flush", 1), flush_volume=params.get("flush_volume", 3), flush_speed=params.get("flush_speed", 0.15),
        post_rinse_vessel=params.get("post_rinse_vessel", "Purge_Solvent_Vessel_2"), post_rinse=params.get("post_rinse", 1), post_rinse_volume=params.get("post_rinse_volume", 1.5), 
        post_rinse_speed=params.get("post_rinse_speed", 0.1),
        
    )


def to_nmr_liquid_transfer_sampling(medusa):
    """
    Transfer reaction mixture to NMR for spectrum acquisition.
    
    This function transfers reaction mixture from the reaction vial to the NMR
    spectrometer for spectrum acquisition. It's used during polymerization
    monitoring and dialysis to track reaction progress and conversion.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.nmr_transfer_params["sampling"]
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="Reaction_Vial", target="NMR", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("volume", 2.1), draw_speed=params.get("draw_speed", 0.05), dispense_speed=params.get("dispense_speed", 0.05),
        post_rinse_vessel=params.get("post_rinse_vessel", "Purge_Solvent_Vessel_2"), post_rinse=params.get("post_rinse", 1), post_rinse_volume=params.get("post_rinse_volume", 2),
        post_rinse_speed=params.get("post_rinse_speed", 0.1),
        
    )


def from_nmr_liquid_transfer_sampling(medusa):
    """
    Transfer reaction mixture from NMR back to reaction vial after spectrum acquisition.
    
    This function returns the reaction mixture from the NMR spectrometer back to
    the reaction vial after spectrum acquisition. It's called after each NMR
    measurement to maintain the reaction volume and continue the polymerization
    or dialysis process.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.nmr_transfer_params["sampling"]
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="NMR", target="Reaction_Vial", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("volume", 2.1), draw_speed=params.get("draw_speed", 0.05), dispense_speed=params.get("dispense_speed", 0.05),
        flush=params.get("flush", 1), flush_volume=params.get("flush_volume", 3), flush_speed=params.get("flush_speed", 0.15),
        post_rinse_vessel=params.get("post_rinse_vessel", "Purge_Solvent_Vessel_2"),
        post_rinse=params.get("post_rinse", 1), post_rinse_volume=params.get("post_rinse_volume", 2),
        post_rinse_speed=params.get("post_rinse_speed", 0.1),
        
    ) 
    medusa.logger.info("Closing gas valve...") #closing gas valve to flush the syringe path to reaction vial
    medusa.write_serial("Gas_Valve", "GAS_OFF")


def to_nmr_liquid_transfer_cleaning(medusa):
    """
    Transfer purge solvet to NMR for cleaning
    
    This function transfers purge solvent from the purge solvent vessel to the NMR
    spectrometer to clean the flow cell.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.cleaning_params
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="Purge_Solvent_Vessel_2", target="NMR", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("nmr_cleaning_volume", 2.1), draw_speed=params.get("nmr_cleaning_draw_speed", 0.1), dispense_speed=params.get("nmr_cleaning_dispense_speed", 0.05),       
    )


def from_nmr_liquid_transfer_cleaning(medusa):
    """
    Transfer purge solvent back from NMR to waste.
    
    This function transfers the purge solvent back from the NMR flow cell after 
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.cleaning_params
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="NMR", target="Waste_Vessel", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("nmr_cleaning_volume", 2.1), draw_speed=params.get("nmr_cleaning_dispense_speed", 0.1), dispense_speed=params.get("nmr_cleaning_draw_speed", 0.05),       
    ) #draw speed = nmr_cleaning_dispense_speed and the other way around because we now remove the cleaning solvent from the nmr


def nmr_flush_gas_cleaning(medusa): 
    """
    Transfer inert gas to the NMR cell to flush out the remaining liquid in the flow cell after cleaning with solvent.
    
    Args:
        medusa: Medusa instance for hardware control
        
    Returns:
        None: Transfer is performed via error-safe wrapper
    """
    params = config.cleaning_params
    
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="Purge_Solvent_Vessel_2", target="NMR", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "gas"),
        volume=params.get("nmr_cleaning_gas_volume", 4), draw_speed=params.get("nmr_cleaning_gas_draw_speed", 0.1), dispense_speed=params.get("nmr_cleaning_gas_dispense_speed", 0.05),       
    ) 




def clean_reaction_vial_transfers_to_vial(medusa):
    """
    Dispense purge solvent to reaction vial to clean it
   
    
    Args:
        medusa: Medusa instance for hardware control
            
    Returns:
        None: Dispenses are performed via error-safe transfer functions
    """
    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Purge_Solvent_Vessel_1", "target": "Reaction_Vial", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": "liquid",
        "volume": config.cleaning_params.get("cleaning_volume_each_pump", 6.0), "draw_speed": config.cleaning_params.get("draw_speed_each_pump", 0.1), "dispense_speed": config.cleaning_params.get("dispense_speed_each_pump", 0.1),
        "flush": config.cleaning_params.get("flush_times_each_pump", 1), "flush_volume": config.cleaning_params.get("flush_volume_each_pump", 5),  
    })

    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Purge_Solvent_Vessel_1", "target": "Reaction_Vial", "pump_id": "Precipitation_Pump",
        "transfer_type": "liquid",
        "volume": config.cleaning_params.get("cleaning_volume_each_pump", 6.0), "draw_speed": config.cleaning_params.get("draw_speed_each_pump", 0.1), "dispense_speed": config.cleaning_params.get("dispense_speed_each_pump", 0.1),
        "flush": config.cleaning_params.get("flush_times_each_pump", 1), "flush_volume": config.cleaning_params.get("flush_volume_each_pump", 5),  
    })

    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Purge_Solvent_Vessel_1", "target": "Reaction_Vial", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": "liquid",
        "volume": config.cleaning_params.get("cleaning_volume_each_pump", 6.0), "draw_speed": config.cleaning_params.get("draw_speed_each_pump", 0.1), "dispense_speed": config.cleaning_params.get("dispense_speed_each_pump", 0.1),
        "flush": config.cleaning_params.get("flush_times_each_pump", 1), "flush_volume": config.cleaning_params.get("flush_volume_each_pump", 5), 
    })

    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Purge_Solvent_Vessel_2", "target": "Reaction_Vial", "pump_id": "Analytical_Pump",
        "transfer_type": "liquid",
        "volume": config.cleaning_params.get("cleaning_volume_each_pump", 6.0), "draw_speed": config.cleaning_params.get("draw_speed_each_pump", 0.1), "dispense_speed": config.cleaning_params.get("dispense_speed_each_pump", 0.1),
        "flush": config.cleaning_params.get("flush_times_each_pump", 1), "flush_volume": config.cleaning_params.get("flush_volume_each_pump", 5),  
    })

   