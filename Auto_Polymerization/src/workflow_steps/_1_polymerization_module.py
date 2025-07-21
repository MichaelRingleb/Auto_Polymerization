"""
Auto_Polymerization Polymerization Module

This module handles the complete polymerization reaction workflow, including:
- Component transfer (solvent, monomer, CTA, initiator)
- Active deoxygenation with argon gas
- Pre-polymerization NMR setup and t0 measurements
- Reaction initiation with temperature control
- Comprehensive error handling and logging

Key Features:
- Error-safe liquid transfers with COM port conflict handling
- Config-driven parameters for all operations
- Active deoxygenation with configurable pump ID
- Pre-polymerization NMR shimming and baseline measurements
- Modular design for easy testing and maintenance

All user-editable settings (volumes, draw/dispense speeds, temperatures, timings, etc.) 
should be set in users/config/platform_config.py and supplied as arguments from the controller.

All polymerization transfers use serial_communication_error_safe_transfer_volumetric, 
a direct, parameter-preserving, error-safe wrapper for medusa.transfer_volumetric. 
All transfer parameters are passed through unchanged. The only difference is robust 
retry logic for COM port conflicts.

All functions are designed to be called from a workflow controller script.

WORKFLOW ORDER (maintained in run_polymerization_workflow):
1. Transfer reaction components (solvent, monomer, CTA, initiator)
2. Deoxygenate reaction mixture with active argon pumping
3. Perform pre-polymerization setup (shimming + t0 measurements)
4. Start polymerization reaction with temperature control

Dependencies:
- medusa: Hardware control framework
- src.liquid_transfers.liquid_transfers_utils: Error-safe transfer functions
- src.NMR.nmr_utils: NMR shimming and analysis utilities
- users.config.platform_config: Configuration parameters

Author: Michael Ringleb (with help from cursor.ai)
Date: [Current Date]
Version: 1.0
"""

from src.liquid_transfers.liquid_transfers_utils import serial_communication_error_safe_transfer_volumetric, deoxygenate_reaction_mixture
from src.NMR.nmr_utils import perform_nmr_shimming_with_retry, acquire_multiple_t0_measurements
import time


# =============================================================================
# COMPONENT TRANSFER FUNCTIONS
# =============================================================================

def transfer_reaction_components(medusa, polymerization_params):
    """
    Transfer all reaction components (solvent, monomer, CTA, initiator) to the reaction vial.
    
    This function performs the complete component transfer sequence for polymerization.
    It transfers solvent, monomer, chain transfer agent (CTA), and initiator in sequence,
    using configurable parameters for volumes, speeds, and cleaning operations.
    
    All transfers use error-safe transfer logic with COM port conflict handling.
    Each transfer includes pre-rinse, flush, and post-rinse operations to ensure
    complete delivery and proper cleaning of the transfer path.
    
    Args:
        medusa: Medusa instance for hardware control
        polymerization_params (dict): Dictionary containing all polymerization transfer parameters
            including volumes, speeds, flush settings, rinse parameters, etc.
            
    Returns:
        None: Component transfers are performed via error-safe transfer functions
    """
    medusa.logger.info("Opening gas valve...") #opening gas valve to  flush the syringe path to reaction vial
    medusa.write_serial("Gas_Valve", "GAS_ON")

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
        "post_rinse_vessel": polymerization_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": polymerization_params.get("post_rinse", 1), "post_rinse_volume": polymerization_params.get("post_rinse_volume", 2.5), 
        "post_rinse_speed": polymerization_params.get("post_rinse_speed", 0.1)
    })
    
    medusa.logger.info("Closing gas valve...") #closing gas valve 
    medusa.write_serial("Gas_Valve", "GAS_OFF")

    medusa.logger.info("All reaction components transferred successfully.")


# =============================================================================
# NMR SHIMMING FUNCTIONS
# =============================================================================

def perform_pre_polymerization_shimming(medusa, max_retries=5, shim_level=1):
    """
    Perform NMR shimming before polymerization starts.
    
    Args:
        medusa: Medusa instance
        max_retries: Maximum number of shimming attempts
        shim_level: Shimming level (default: 1)
        
    Returns:
        dict: Shimming results with success status
    """
    medusa.logger.info("Performing pre-polymerization NMR shimming...")
    
    shim_result = perform_nmr_shimming_with_retry(medusa, max_retries=max_retries, shim_level=shim_level)
    
    if shim_result['success']:
        medusa.logger.info("Pre-polymerization shimming completed successfully.")
    else:
        medusa.logger.error(f"Pre-polymerization shimming failed: {shim_result['error_message']}")
    
    return shim_result


def perform_post_t0_shimming(medusa, max_retries=5, shim_level=1):
    """
    Perform NMR shimming after t0 measurements and before starting monitoring.
    
    Args:
        medusa: Medusa instance
        max_retries: Maximum number of shimming attempts
        shim_level: Shimming level (default: 1)
        
    Returns:
        dict: Shimming results with success status
    """
    medusa.logger.info("Performing post-t0 NMR shimming...")
    
    shim_result = perform_nmr_shimming_with_retry(medusa, max_retries=max_retries, shim_level=shim_level)
    
    if shim_result['success']:
        medusa.logger.info("Post-t0 shimming completed successfully.")
    else:
        medusa.logger.error(f"Post-t0 shimming failed: {shim_result['error_message']}")
    
    return shim_result


# =============================================================================
# T0 BASELINE MEASUREMENT FUNCTIONS
# =============================================================================

def acquire_t0_baseline_measurements(medusa, monitoring_params, experiment_id, num_measurements=3, nmr_data_base_path=None):
    """
    Acquire multiple t0 measurements for baseline calculation.
    
    Args:
        medusa: Medusa instance
        monitoring_params: dict containing monitoring parameters
        experiment_id: Experiment identifier for filenames
        num_measurements: Number of t0 measurements to perform
        nmr_data_base_path: Base path for saving NMR data
        
    Returns:
        dict: t0 baseline results with individual measurements and averages
    """
    medusa.logger.info(f"Acquiring {num_measurements} t0 baseline measurements...")
    
    t0_result = acquire_multiple_t0_measurements(
                    medusa, monitoring_params, experiment_id, num_measurements=num_measurements, nmr_data_base_path=nmr_data_base_path
    )
    
    if t0_result['success']:
        medusa.logger.info(f"t0 baseline established from {t0_result['successful_count']}/{t0_result['total_count']} measurements")
    else:
        medusa.logger.error(f"t0 baseline acquisition failed: {t0_result.get('error_message', 'Unknown error')}")
    
    return t0_result


def perform_pre_polymerization_setup(medusa, monitoring_params, experiment_id, nmr_data_base_path=None):
    """
    Perform complete pre-polymerization setup including shimming and t0 measurements.
    
    This function handles the complete setup process before the polymerization reaction starts:
    1. Pre-polymerization shimming (critical - stops workflow if fails)
    2. Multiple t0 measurements for baseline
    3. Post-t0 shimming before monitoring starts
    
    Args:
        medusa: Medusa instance
        monitoring_params: dict containing monitoring parameters
        experiment_id: Experiment identifier for filenames
        nmr_data_base_path: Base path for saving NMR data
        
    Returns:
        dict: Complete setup results including t0 baseline data
    """
    medusa.logger.info("Starting pre-polymerization setup...")
    
    # Step 1: Pre-polymerization shimming (critical)
    pre_shim_result = perform_pre_polymerization_shimming(medusa, max_retries=5, shim_level=1)
    if not pre_shim_result['success']:
        medusa.logger.error("Pre-polymerization shimming failed - stopping workflow")
        return {
            'success': False,
            'error_message': f"Pre-polymerization shimming failed: {pre_shim_result['error_message']}",
            't0_baseline': None
        }
    
    # Step 2: Acquire t0 baseline measurements
    t0_result = acquire_t0_baseline_measurements(medusa, monitoring_params, experiment_id, num_measurements=3, nmr_data_base_path=nmr_data_base_path)
    if not t0_result['success']:
        medusa.logger.error("t0 baseline acquisition failed - stopping workflow")
        return {
            'success': False,
            'error_message': f"t0 baseline acquisition failed: {t0_result.get('error_message', 'Unknown error')}",
            't0_baseline': None
        }
    
    # Step 3: Post-t0 shimming
    post_shim_result = perform_post_t0_shimming(medusa, max_retries=5, shim_level=1)
    if not post_shim_result['success']:
        medusa.logger.warning(f"Post-t0 shimming failed: {post_shim_result['error_message']} - continuing with monitoring")
    
    medusa.logger.info("Pre-polymerization setup completed successfully.")
    
    return {
        'success': True,
        'pre_shim_result': pre_shim_result,
        't0_baseline': t0_result,
        'post_shim_result': post_shim_result
    }


# =============================================================================
# REACTION CONTROL FUNCTIONS
# =============================================================================

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
        time.sleep(15)
        real_temp = medusa.get_hotplate_rpm("Reaction_Vial")
        if medusa.get_hotplate_temperature("Reaction_Vial")  < polymerization_temp - 2:
            medusa.logger.info(f"Heatplate temperature {real_temp} C is below target temperature {polymerization_temp} C, waiting for it to reach target temperature")
           

    # Lower vial into heatplate
    medusa.write_serial("Linear_Actuator", "1000")
    medusa.logger.info("Reaction vial lowered into heatplate. Polymerization started.")


# =============================================================================
# MAIN WORKFLOW FUNCTION
# =============================================================================

def run_polymerization_workflow(medusa, polymerization_params, polymerization_temp, set_rpm, deoxygenation_time, monitoring_params=None, experiment_id=None, nmr_data_base_path=None):
    """
    Execute the complete polymerization workflow including pre-polymerization setup.
    
    WORKFLOW ORDER:
    1. Transfer reaction components
    2. Deoxygenate reaction mixture  
    3. Perform pre-polymerization setup (shimming + t0 measurements)
    4. Start polymerization reaction
    
    Args:
        medusa: Medusa instance
        polymerization_params: dict containing all polymerization transfer parameters
        polymerization_temp: Target polymerization temperature
        set_rpm: Stirring speed (rpm)
        deoxygenation_time: Time to deoxygenate reaction mixture in seconds
        monitoring_params: dict containing monitoring parameters (for t0 measurements)
        experiment_id: Experiment identifier for filenames
        nmr_data_base_path: Base path for saving NMR data
        
    Returns:
        dict: Complete workflow results including t0 baseline data
    """
    medusa.logger.info("Starting polymerization workflow...")
    
    # Step 1: Open gas valve for flush steps in component transfers
    medusa.write_serial("Gas_Valve", "GAS_ON")
    
    # Step 2: Transfer all reaction components
    transfer_reaction_components(medusa, polymerization_params)
    
    # Step 3: Deoxygenate reaction mixture (active pumping mode)
    deoxygenate_reaction_mixture(medusa, deoxygenation_time, pump_id="Solvent_Monomer_Modification_Pump")
    
    # Close gas valve
    medusa.write_serial("Gas_Valve", "GAS_OFF")
    
    # Step 4: Perform pre-polymerization setup (shimming + t0 measurements)
    if monitoring_params and experiment_id:
        setup_result = perform_pre_polymerization_setup(medusa, monitoring_params, experiment_id, nmr_data_base_path)
        if not setup_result['success']:
            medusa.logger.error("Pre-polymerization setup failed - stopping workflow")
            return {
                'success': False,
                'error_message': setup_result['error_message'],
                't0_baseline': None
            }
        t0_baseline = setup_result['t0_baseline']
    else:
        medusa.logger.warning("No monitoring parameters provided - skipping t0 measurements")
        t0_baseline = None

    # Step 5: Start polymerization reaction
    start_polymerization_reaction(medusa, polymerization_temp, set_rpm)
    
    medusa.logger.info("Polymerization workflow completed successfully.")
    
    return {
        'success': True,
        't0_baseline': t0_baseline
    }