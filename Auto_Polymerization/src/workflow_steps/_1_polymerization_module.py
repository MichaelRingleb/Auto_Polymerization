"""
_1_polymerization_module.py

Polymerization module for the Auto_Polymerization workflow.
Encapsulates all steps required to perform the polymerization reaction, including component transfer,
deoxygenation, temperature control, and reaction monitoring.

All user-editable settings (volumes, draw/dispense speeds, temperatures, timings, etc.) should be set 
in users/config/platform_config.py and supplied as arguments from the controller.

All polymerization transfers use serial_communication_error_safe_transfer_volumetric, a direct, 
parameter-preserving, error-safe wrapper for medusa.transfer_volumetric. All transfer parameters 
are passed through unchanged. The only difference is robust retry logic for COM port conflicts.

All functions are designed to be called from a workflow controller script.
"""
from src.liquid_transfers.liquid_transfers_utils import serial_communication_error_safe_transfer_volumetric
import time


def transfer_reaction_components(medusa, polymerization_params):
    """
    Transfer all reaction components (solvent, monomer, CTA, initiator) to the reaction vial.
    Uses error-safe transfer logic with config-driven parameters.
    
    Args:
        medusa: Medusa instance for liquid handling
        polymerization_params: dict containing all polymerization transfer parameters
    """
    medusa.logger.info("Transferring reaction components to reaction vial...")
    
    # Transfer solvent
    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Solvent_Vessel", "target": "Reaction_Vial", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": "liquid",
        "pre_rinse": polymerization_params.get("pre_rinse", 1), "pre_rinse_volume": polymerization_params.get("pre_rinse_volume", 0.5), "pre_rinse_speed": polymerization_params.get("pre_rinse_speed", 0.1),
        "volume": polymerization_params.get("solvent_volume", 10), "draw_speed": polymerization_params.get("solvent_draw_speed", 0.08), "dispense_speed": polymerization_params.get("solvent_dispense_speed", 0.13),
        "flush": polymerization_params.get("flush", 2), "flush_volume": polymerization_params.get("flush_volume", 5), "flush_speed": polymerization_params.get("flush_speed", 0.3),
        "post_rinse_vessel": polymerization_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": polymerization_params.get("post_rinse", 1), "post_rinse_volume": polymerization_params.get("post_rinse_volume", 2.5), 
        "post_rinse_speed": polymerization_params.get("post_rinse_speed", 0.1)
    })
    
    # Transfer monomer
    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Monomer_Vessel", "target": "Reaction_Vial", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": "liquid",
        "pre_rinse": polymerization_params.get("pre_rinse", 1), "pre_rinse_volume": polymerization_params.get("pre_rinse_volume", 0.5), "pre_rinse_speed": polymerization_params.get("pre_rinse_speed", 0.1),
        "volume": polymerization_params.get("monomer_volume", 4), "draw_speed": polymerization_params.get("monomer_draw_speed", 0.08), "dispense_speed": polymerization_params.get("monomer_dispense_speed", 0.13),
        "flush": polymerization_params.get("flush", 2), "flush_volume": polymerization_params.get("flush_volume", 5), "flush_speed": polymerization_params.get("flush_speed", 0.3),
        "post_rinse_vessel": polymerization_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": polymerization_params.get("post_rinse", 1), "post_rinse_volume": polymerization_params.get("post_rinse_volume", 2.5), 
        "post_rinse_speed": polymerization_params.get("post_rinse_speed", 0.1)
    })
    
    # Transfer CTA
    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "CTA_Vessel", "target": "Reaction_Vial", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": "liquid",
        "pre_rinse": polymerization_params.get("pre_rinse", 1), "pre_rinse_volume": polymerization_params.get("pre_rinse_volume", 0.5), "pre_rinse_speed": polymerization_params.get("pre_rinse_speed", 0.1),
        "volume": polymerization_params.get("cta_volume", 4), "draw_speed": polymerization_params.get("cta_draw_speed", 0.08), "dispense_speed": polymerization_params.get("cta_dispense_speed", 0.13),
        "flush": polymerization_params.get("flush", 2), "flush_volume": polymerization_params.get("flush_volume", 5), "flush_speed": polymerization_params.get("flush_speed", 0.3),
        "post_rinse_vessel": polymerization_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": polymerization_params.get("post_rinse", 1), "post_rinse_volume": polymerization_params.get("post_rinse_volume", 2.5), 
        "post_rinse_speed": polymerization_params.get("post_rinse_speed", 0.1)
    })
    
    # Transfer initiator
    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Initiator_Vessel", "target": "Reaction_Vial", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": "liquid",
        "pre_rinse": polymerization_params.get("pre_rinse", 1), "pre_rinse_volume": polymerization_params.get("pre_rinse_volume", 0.5), "pre_rinse_speed": polymerization_params.get("pre_rinse_speed", 0.1),
        "volume": polymerization_params.get("initiator_volume", 3), "draw_speed": polymerization_params.get("initiator_draw_speed", 0.08), "dispense_speed": polymerization_params.get("initiator_dispense_speed", 0.13),
        "flush": polymerization_params.get("flush", 2), "flush_volume": polymerization_params.get("flush_volume", 5), "flush_speed": polymerization_params.get("flush_speed", 0.3),
        "post_rinse_vessel": polymerization_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": polymerization_params.get("post_rinse", 1), "last_post_rinse_volume": polymerization_params.get("post_rinse_volume", 5), 
        "post_rinse_speed": polymerization_params.get("post_rinse_speed", 0.1)
    })
    
    medusa.logger.info("All reaction components transferred successfully.")


def deoxygenate_reaction_mixture(medusa, deoxygenation_time):
    """
    Deoxygenate the reaction mixture for the specified time.
    
    Args:
        medusa: Medusa instance
        deoxygenation_time: Time to deoxygenate reaction mixture in seconds
    """
    medusa.logger.info(f"Deoxygenating reaction mixture for {deoxygenation_time} seconds...")
    time.sleep(deoxygenation_time)
    medusa.logger.info("Deoxygenation complete.")


def start_polymerization_reaction(medusa, polymerization_temp, set_rpm):
    """
    Start the polymerization reaction by lowering the vial into the heatplate.
    
    Args:
        medusa: Medusa instance
        polymerization_temp: Target polymerization temperature
        set_rpm: Stirring speed (rpm)
    """
    medusa.logger.info(f"Starting polymerization at {polymerization_temp}°C with {set_rpm} RPM...")
    
    # Wait for heatplate to reach target temperature
    while medusa.get_hotplate_temperature("Reaction_Vial") < polymerization_temp - 2:
        time.sleep(2)
        medusa.get_hotplate_rpm("Reaction_Vial")
    
    # Lower vial into heatplate
    medusa.write_serial("Linear_Actuator", "1000")
    medusa.logger.info("Reaction vial lowered into heatplate. Polymerization started.")


def run_polymerization_workflow(medusa, polymerization_params, polymerization_temp, set_rpm, deoxygenation_time):
    """
    Execute the complete polymerization workflow.
    
    Args:
        medusa: Medusa instance
        polymerization_params: dict containing all polymerization transfer parameters
        polymerization_temp: Target polymerization temperature
        set_rpm: Stirring speed (rpm)
        deoxygenation_time: Time to deoxygenate reaction mixture in seconds
    """
    medusa.logger.info("Starting polymerization workflow...")
    
    # Open gas valve for flush steps
    medusa.write_serial("Gas_Valve", "GAS_ON")
    
    # Transfer all reaction components
    transfer_reaction_components(medusa, polymerization_params)
    
    # Deoxygenate reaction mixture
    deoxygenate_reaction_mixture(medusa, deoxygenation_time)
    
    # Close gas valve
    medusa.write_serial("Gas_Valve", "GAS_OFF")
    
    # Start polymerization reaction
    start_polymerization_reaction(medusa, polymerization_temp, set_rpm)
    
    medusa.logger.info("Polymerization workflow completed successfully.")