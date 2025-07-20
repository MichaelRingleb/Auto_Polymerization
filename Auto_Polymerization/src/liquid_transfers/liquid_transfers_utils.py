"""
liquid_transfers_utils.py

Utility functions for robust and modular liquid transfers in the Auto_Polymerization platform.

This module provides wrappers and helpers for all analytical and workflow-related liquid transfers.
The key function, serial_communication_error_safe_transfer_volumetric, is a direct, parameter-preserving,
error-safe wrapper for medusa.transfer_volumetric. It adds robust retry logic for COM port conflicts,
ensuring that all transfer parameters and behavior remain unchanged except for the added error handling.

All transfer parameters (source, target, pump_id, transfer_type, volume, draw_speed, dispense_speed, pre_rinse, etc.)
are passed through unchanged to medusa.transfer_volumetric. No parameter names, defaults, or logic are altered.

Use this module to ensure all hardware communication is robust to serial port contention in multithreaded workflows.
"""
import time
from serial.serialutil import SerialException
from users.config import platform_config as config


def retry_on_serial_com_error(func, max_retries=3, initial_delay=120, max_delay=300, logger=None):
    """
    Retry a function that might fail due to COM port errors.
    Implements exponential backoff for COM port permission errors.
    If logger is provided, uses logger for messages; otherwise falls back to print.
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

    All parameters are passed through unchanged to medusa.transfer_volumetric.
    The only difference is robust retry logic for COM port conflicts (PermissionError),
    with exponential backoff and clear logging. No transfer logic or parameter names are changed.
    """
    def transfer_func():
        return medusa.transfer_volumetric(**kwargs)
    return retry_on_serial_com_error(transfer_func, logger=logger)


def uv_vis_liquid_transfer(medusa):
    """
    Perform a transfer to the UV-VIS using standardized parameters.
    Args:
        medusa: Medusa instance
        source: Source vessel
        target: Target vessel (usually UV_VIS)
        pump_id: Pump to use
        transfer_params: dict of transfer parameters (volume, draw_speed, etc.)
    """
    params = config.uv_vis_transfer_params
    medusa.transfer_volumetric(
        source="Reaction_Vial", target="UV_VIS", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        pre_rinse=params.get("pre_rinse", 1), pre_rinse_volume=params.get("pre_rinse_volume", 1.0), pre_rinse_speed=params.get("pre_rinse_speed", 0.02),
        volume=params.get("volume", 1.5), draw_speed=params.get("draw_speed", 0.03), dispense_speed=params.get("dispense_speed", 0.016),
        flush=params.get("flush", 1), flush_volume=params.get("flush_volume", 2), flush_speed=params.get("flush_speed", 0.05),
        post_rinse_vessel=params.get("post_rinse_vessel", "Purge_Solvent_Vessel_2"), post_rinse=params.get("post_rinse", 1), post_rinse_volume=params.get("post_rinse_volume", 1.5),
        post_rinse_speed=params.get("post_rinse_speed", 0.01),
        
        
    )

def to_nmr_liquid_transfer_shimming(medusa):
    """
    Transfer deuterated solvent from source to NMR for shimming, using shimming parameters from config.
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
    Transfer deuterated solvent from NMR back to target after shimming, using shimming parameters from config.
    """
    medusa.logger.info("Opening gas valve...") #opening gas valve to  flush the syringe path to reaction vial
    medusa.write_serial("Gas_Valve", "GAS_ON")

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
    medusa.logger.info("Closing gas valve...") #closing gas valve to flush the syringe path to reaction vial
    medusa.write_serial("Gas_Valve", "GAS_OFF")


def to_nmr_liquid_transfer_sampling(medusa):
    """
    Transfer sample from reaction vessel to NMR for sampling, using sampling parameters from config.
    """
    
    params = config.nmr_transfer_params["sampling"]
    serial_communication_error_safe_transfer_volumetric(
        medusa,
        source="Reaction_Vial", target="NMR", pump_id="Analytical_Pump",
        transfer_type=params.get("transfer_type", "liquid"),
        volume=params.get("volume", 2.1), draw_speed=params.get("draw_speed", 0.05), dispense_speed=params.get("dispense_speed", 0.05),
        flush=
        post_rinse_vessel=params.get("post_rinse_vessel", "Purge_Solvent_Vessel_2"), post_rinse=params.get("post_rinse", 1), post_rinse_volume=params.get("post_rinse_volume", 2),
        post_rinse_speed=params.get("post_rinse_speed", 0.1),
        
    )
    

def from_nmr_liquid_transfer_sampling(medusa):
    """
    Transfer sample from NMR back to reaction vessel after sampling, using sampling parameters from config.
    """
    medusa.logger.info("Opening gas valve...") #opening gas valve to  flush the syringe path to reaction vial
    medusa.write_serial("Gas_Valve", "GAS_ON")

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