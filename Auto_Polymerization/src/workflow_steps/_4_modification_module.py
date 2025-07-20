"""
Modification Workflow Module

This module implements the modification/functionalization workflow for the Auto_Polymerization platform.
It includes deoxygenation, UV-VIS reference measurement, modification reagent addition, 
UV-VIS monitoring until reaction completion, and post-modification dialysis.

Key Features:
    - Argon deoxygenation of reaction mixture
    - UV-VIS reference spectrum acquisition with pure solvent
    - Modification reagent addition with proper flushing
    - UV-VIS monitoring with absorbance stability detection
    - Post-modification dialysis using existing dialysis workflow
    - Comprehensive error handling and retry logic
    - Detailed summary file generation (txt and csv)
    - Integration with medusa hardware control framework

Workflow Steps:
    1. Deoxygenation with argon gas
    2. UV-VIS reference spectrum (pure solvent)
    3. UV-VIS t0 spectrum (reaction mixture)
    4. Modification reagent addition
    5. UV-VIS monitoring until reaction completion
    6. Post-modification dialysis
    7. Summary file generation

Dependencies:
    - medusa: Hardware control framework
    - src.UV_VIS.uv_vis_utils: UV-VIS spectroscopy utilities
    - src.workflow_steps._3_dialysis_module: Dialysis workflow
    - users.config.platform_config: Configuration parameters

Author: Michael Ringleb (with help from cursor.ai)
Date: [Current Date]
Version: 1.0
"""

import logging
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import csv

# Import medusa and utilities
from medusa import Medusa
import src.UV_VIS.uv_vis_utils as uv_vis
from src.liquid_transfers.liquid_transfers_utils import to_uv_vis_reference_transfer, to_uv_vis_sampling_transfer, from_uv_vis_cleanup_transfer, add_modification_reagent_transfer, deoxygenate_reaction_mixture

# Import user-editable platform configuration
import users.config.platform_config as config





# Deoxygenation function moved to liquid_transfers_utils.py
# Use: deoxygenate_reaction_mixture(medusa, deoxygenation_time_sec, active_pumping=True)


def setup_uv_vis_reference(medusa: Medusa) -> Tuple[bool, Optional[str]]:
    """
    Set up UV-VIS reference spectrum with pure solvent.
    
    Args:
        medusa: Medusa object for hardware control
        
    Returns:
        Tuple[bool, Optional[str]]: (success, filename if successful)
    """
    
    try:
        medusa.logger.info("Setting up UV-VIS reference spectrum...")
        
        # Add NMR solvent to UV-VIS cell using proper transfer utility
        to_uv_vis_reference_transfer(medusa)
        
        # Take reference spectrum
        spectrum, wavelengths, filename, _, _ = uv_vis.take_spectrum(reference=True)
        
        if spectrum is not None and wavelengths is not None:
            medusa.logger.info(f"UV-VIS reference spectrum saved: {filename}")
            return True, filename
        else:
            medusa.logger.error("Failed to acquire UV-VIS reference spectrum")
            return False, None
            
    except Exception as e:
        medusa.logger.error(f"UV-VIS reference setup failed: {str(e)}")
        return False, None


def setup_uv_vis_t0(medusa: Medusa) -> Tuple[bool, Optional[str]]:
    """
    Set up UV-VIS t0 spectrum with reaction mixture.
    
    Args:
        medusa: Medusa object for hardware control
        
    Returns:
        Tuple[bool, Optional[str]]: (success, filename if successful)
    """

    
    try:
        medusa.logger.info("Setting up UV-VIS t0 spectrum...")
        
        # Remove NMR solvent from UV-VIS cell using proper transfer utility
        from_uv_vis_cleanup_transfer(medusa, target="NMR_Solvent_Vessel", volume=config.uv_vis_transfer_params.get("volume", 1.5))
        
        # Start flow through UV-VIS and measure t0 spectrum using proper transfer utility
        to_uv_vis_sampling_transfer(medusa, volume=config.uv_vis_transfer_params.get("volume", 1.5))
        
        # Take t0 spectrum
        spectrum, wavelengths, filename, _, _ = uv_vis.take_spectrum(t0=True)
        
        if spectrum is not None and wavelengths is not None:
            medusa.logger.info(f"UV-VIS t0 spectrum saved: {filename}")
            return True, filename
        else:
            medusa.logger.error("Failed to acquire UV-VIS t0 spectrum")
            return False, None
            
    except Exception as e:
        medusa.logger.error(f"UV-VIS t0 setup failed: {str(e)}")
        return False, None


def add_modification_reagent(medusa: Medusa, modification_params: Dict) -> bool:
    """
    Add modification reagent to the reaction vial.
    
    Args:
        medusa: Medusa object for hardware control
        modification_params: Modification parameters from config
        
    Returns:
        bool: True if successful, False otherwise
    """
   
    
    try:
        medusa.logger.info("Adding modification reagent...")
        
        # Use error-safe transfer for modification reagent addition
        add_modification_reagent_transfer(medusa)
        
        medusa.logger.info("Modification reagent added successfully")
        return True
        
    except Exception as e:
        medusa.logger.error(f"Modification reagent addition failed: {str(e)}")
        return False


def monitor_modification_reaction(medusa: Medusa, modification_params: Dict) -> Dict:
    """
    Monitor the modification reaction using UV-VIS spectroscopy.
    
    Args:
        medusa: Medusa object for hardware control
        modification_params: Modification parameters from config
        
    Returns:
        Dict: Monitoring results including final conversion and measurement count
    """

    monitoring_interval = config.modification_params["monitoring_interval_minutes"]
    max_iterations = config.modification_params["max_monitoring_iterations"]
    tolerance_percent = config.modification_params["uv_vis_stability_tolerance_percent"]
    stability_measurements = config.modification_params["uv_vis_stability_measurements"]
    
    measurements = []
    iteration = 0
    reaction_complete = False
    final_conversion = None
    
    medusa.logger.info(f"Starting modification reaction monitoring (max {max_iterations} iterations, {monitoring_interval} min intervals)")
    
    while not reaction_complete and iteration < max_iterations:
        try:
            # Transfer reaction mixture to UV-VIS cell using proper transfer utility
            to_uv_vis_sampling_transfer(medusa)
            
            iteration += 1
            medusa.logger.info(f"Modification monitoring iteration {iteration}/{max_iterations}")
            
            # Take UV-VIS measurement and calculate conversion
            spectrum, wavelengths, filename, conversion, reaction_complete = uv_vis.take_spectrum(calculate_conversion=True)
            
            if conversion is not None:
                medusa.logger.info(f"Current conversion: {conversion:.2f}%")
                final_conversion = conversion
                measurements.append({
                    'iteration': iteration,
                    'filename': filename,
                    'conversion': conversion,
                    'timestamp': datetime.now().isoformat()
                })
            
            if reaction_complete:
                medusa.logger.info("Modification reaction completed based on absorbance stability")
                break
            
            # Wait before next measurement
            if iteration < max_iterations:
                medusa.logger.info(f"Waiting {monitoring_interval} minutes before next measurement...")
                time.sleep(monitoring_interval * 60)
                
        except Exception as e:
            medusa.logger.error(f"UV-VIS measurement failed at iteration {iteration}: {str(e)}")
            # Retry logic (2 retries)
            for retry in range(2):
                try:
                    medusa.logger.info(f"Retrying UV-VIS measurement (attempt {retry + 1}/2)...")
                    time.sleep(30)  # Wait 30 seconds before retry
                    spectrum, wavelengths, filename, conversion, reaction_complete = uv_vis.take_spectrum(calculate_conversion=True)
                    if conversion is not None:
                        medusa.logger.info(f"Retry successful - conversion: {conversion:.2f}%")
                        break
                except Exception as retry_e:
                    medusa.logger.error(f"Retry {retry + 1} failed: {str(retry_e)}")
    
    if iteration >= max_iterations:
        medusa.logger.warning(f"Modification monitoring stopped after {max_iterations} iterations")
        if final_conversion is not None:
            medusa.logger.info(f"Final conversion achieved: {final_conversion:.2f}%")
    else:
        medusa.logger.info(f"Modification completed successfully in {iteration} iterations")
        if final_conversion is not None:
            medusa.logger.info(f"Final conversion: {final_conversion:.2f}%")
    
    return {
        'success': True,
        'total_iterations': iteration,
        'final_conversion': final_conversion,
        'reaction_complete': reaction_complete,
        'measurements': measurements
    }


# Post-modification dialysis is now handled directly in the platform controller
# using the existing dialysis workflow with time-based stopping


def generate_modification_summary(experiment_id: str, data_base_path: str, 
                                monitoring_results: Dict, modification_params: Dict) -> Dict:
    """
    Generate summary files for the modification workflow.
    
    Args:
        experiment_id: Experiment identifier
        data_base_path: Base path for data storage
        monitoring_results: Results from modification monitoring
        modification_params: Modification parameters used
        
    Returns:
        Dict: Paths to generated summary files
    """
    logger = logging.getLogger(__name__)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_path = Path(data_base_path)
    base_path.mkdir(parents=True, exist_ok=True)
    
    # Generate detailed summary (txt)
    summary_txt = base_path / f"{experiment_id}_modification_summary_{timestamp}.txt"
    
    try:
        with open(summary_txt, 'w') as f:
            f.write(f"Modification Workflow Summary\n")
            f.write(f"Experiment ID: {experiment_id}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write(f"Parameters Used:\n")
            f.write(f"- Modification volume: {modification_params['modification_volume']} mL\n")
            f.write(f"- Deoxygenation time: {modification_params['deoxygenation_time_sec']} s\n")
            f.write(f"- Monitoring interval: {modification_params['monitoring_interval_minutes']} min\n")
            f.write(f"- Max iterations: {modification_params['max_monitoring_iterations']}\n")
            f.write(f"- Post-modification dialysis: {modification_params['post_modification_dialysis_hours']} h\n")
            f.write(f"- UV-VIS stability tolerance: {modification_params['uv_vis_stability_tolerance_percent']}%\n")
            f.write(f"- UV-VIS stability measurements: {modification_params['uv_vis_stability_measurements']}\n\n")
            
            f.write(f"Results:\n")
            f.write(f"- Total iterations: {monitoring_results['total_iterations']}\n")
            f.write(f"- Final conversion: {monitoring_results['final_conversion']:.2f}%\n")
            f.write(f"- Reaction complete: {monitoring_results['reaction_complete']}\n\n")
            
            f.write(f"Measurements:\n")
            for measurement in monitoring_results['measurements']:
                f.write(f"- Iteration {measurement['iteration']}: {measurement['conversion']:.2f}% ({measurement['filename']})\n")
        
        logger.info(f"Detailed summary saved to: {summary_txt}")
        
    except Exception as e:
        logger.error(f"Failed to write detailed summary: {str(e)}")
        summary_txt = None
    
    # Generate CSV summary with absorbance values
    summary_csv = base_path / f"{experiment_id}_modification_absorbance_{timestamp}.csv"
    
    try:
        with open(summary_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Iteration', 'Filename', 'Conversion (%)', 'Timestamp'])
            
            for measurement in monitoring_results['measurements']:
                writer.writerow([
                    measurement['iteration'],
                    measurement['filename'],
                    f"{measurement['conversion']:.2f}",
                    measurement['timestamp']
                ])
        
        logger.info(f"CSV summary saved to: {summary_csv}")
        
    except Exception as e:
        logger.error(f"Failed to write CSV summary: {str(e)}")
        summary_csv = None
    
    return {
        'summary_txt': str(summary_txt) if summary_txt else None,
        'summary_csv': str(summary_csv) if summary_csv else None
    }


def run_modification_workflow(medusa: Medusa, 
                            modification_params: Optional[Dict] = None,
                            experiment_id: Optional[str] = None,
                            data_base_path: Optional[str] = None,
                            uv_vis_data_base_path: Optional[str] = None) -> Dict:
    """
    Run the complete modification workflow.
    
    Args:
        medusa: Medusa object for hardware control
        modification_params: Modification parameters (uses config if None)
        experiment_id: Experiment identifier (uses config if None)
        data_base_path: Base path for data storage (uses config if None)
        uv_vis_data_base_path: UV-VIS data path (uses config if None)
        
    Returns:
        Dict: Complete workflow results
    """
    # Use config values if not provided
    if modification_params is None:
        modification_params = config.modification_params
    if experiment_id is None:
        experiment_id = config.experiment_id
    if data_base_path is None:
        data_base_path = config.data_base_path
    if uv_vis_data_base_path is None:
        uv_vis_data_base_path = config.uv_vis_data_base_path
    
   
    
    medusa.logger.info(f"Starting modification workflow for experiment {experiment_id}")
    
    workflow_results = {
        'success': False,
        'experiment_id': experiment_id,
        'workflow_steps': {},
        'summary_files': {},
        'error_message': None
    }
    
    try:
        # Step 1: Deoxygenation
        medusa.logger.info("Step 1: Deoxygenation")
        deoxygenation_success = deoxygenate_reaction_mixture(
            medusa, 
            modification_params["deoxygenation_time_sec"],
            pump_id="Solvent_Monomer_Modification_Pump"
        )
        workflow_results['workflow_steps']['deoxygenation'] = {
            'success': deoxygenation_success,
            'duration_sec': modification_params["deoxygenation_time_sec"]
        }
        
        if not deoxygenation_success:
            raise Exception("Deoxygenation failed")
        
        # Step 2: UV-VIS reference setup
        medusa.logger.info("Step 2: UV-VIS reference setup")
        ref_success, ref_filename = setup_uv_vis_reference(medusa)
        workflow_results['workflow_steps']['uv_vis_reference'] = {
            'success': ref_success,
            'filename': ref_filename
        }
        
        if not ref_success:
            raise Exception("UV-VIS reference setup failed")
        
        # Step 3: UV-VIS t0 setup
        medusa.logger.info("Step 3: UV-VIS t0 setup")
        t0_success, t0_filename = setup_uv_vis_t0(medusa)
        workflow_results['workflow_steps']['uv_vis_t0'] = {
            'success': t0_success,
            'filename': t0_filename
        }
        
        if not t0_success:
            raise Exception("UV-VIS t0 setup failed")
        
        # Step 4: Add modification reagent
        medusa.logger.info("Step 4: Add modification reagent")
        reagent_success = add_modification_reagent(medusa, modification_params)
        workflow_results['workflow_steps']['reagent_addition'] = {
            'success': reagent_success,
            'volume_ml': modification_params["modification_volume"]
        }
        
        if not reagent_success:
            raise Exception("Modification reagent addition failed")
        
        # Step 5: Monitor modification reaction
        medusa.logger.info("Step 5: Monitor modification reaction")
        monitoring_results = monitor_modification_reaction(medusa, modification_params)
        workflow_results['workflow_steps']['monitoring'] = monitoring_results
        
        if not monitoring_results['success']:
            raise Exception("Modification monitoring failed")
        
        # Step 6: Post-modification dialysis is handled in platform controller
        medusa.logger.info("Step 6: Post-modification dialysis (handled in platform controller)")
        workflow_results['workflow_steps']['post_dialysis'] = {
            'success': True,
            'note': 'Handled in platform controller'
        }
        
        # Step 7: Generate summary files
        medusa.logger.info("Step 7: Generate summary files")
        summary_files = generate_modification_summary(
            experiment_id, 
            data_base_path, 
            monitoring_results, 
            modification_params
        )
        workflow_results['summary_files'] = summary_files
        
        # Workflow completed successfully
        workflow_results['success'] = True
        workflow_results['final_conversion'] = monitoring_results['final_conversion']
        workflow_results['total_iterations'] = monitoring_results['total_iterations']
        
        medusa.logger.info(f"Modification workflow completed successfully")
        medusa.logger.info(f"Final conversion: {monitoring_results['final_conversion']:.2f}%")
        medusa.logger.info(f"Total iterations: {monitoring_results['total_iterations']}")
        
        if summary_files['summary_txt']:
            medusa.logger.info(f"Summary file: {summary_files['summary_txt']}")
        if summary_files['summary_csv']:
            medusa.logger.info(f"CSV file: {summary_files['summary_csv']}")
        
    except Exception as e:
        error_msg = f"Modification workflow failed: {str(e)}"
        medusa.logger.error(error_msg)
        workflow_results['error_message'] = error_msg
        workflow_results['success'] = False
    
    return workflow_results
