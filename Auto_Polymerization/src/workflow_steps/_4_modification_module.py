"""
Auto_Polymerization Modification Module

This module implements the complete modification/functionalization workflow for the Auto_Polymerization platform.
It handles UV-VIS-based functionalization reactions with comprehensive monitoring and analysis.

Key Features:
- Active argon deoxygenation of reaction mixture
- UV-VIS reference spectrum acquisition with pure solvent
- UV-VIS t0 spectrum acquisition with reaction mixture
- Modification reagent addition with proper flushing, rinsing, and hotplate control
- UV-VIS monitoring with absorbance stability detection
- Post-modification dialysis using existing dialysis workflow
- Comprehensive error handling and retry logic
- Detailed summary file generation (txt and csv formats)
- Integration with medusa hardware control framework
- Error-safe liquid transfers with COM port conflict handling
- Final argon push to UV/VIS cell for safe clearing
- Hotplate temperature and vial movement control

Workflow Steps:
1. Deoxygenation with argon gas (active pumping)
2. UV-VIS reference spectrum (pure solvent reference)
3. UV-VIS t0 spectrum (reaction mixture before modification)
4. Modification reagent addition with hotplate and vial control
5. UV-VIS monitoring until reaction completion (absorbance stability)
6. Post-modification dialysis for purification
7. Summary file generation with detailed results
8. Final argon push to UV/VIS cell

All liquid transfers use error-safe functions with COM port conflict handling.
All parameters are configurable through platform_config.py.

Dependencies:
- medusa: Hardware control framework
- src.UV_VIS.uv_vis_utils: UV-VIS spectroscopy utilities
- src.liquid_transfers.liquid_transfers_utils: Error-safe transfer functions
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




def setup_uv_vis_reference(medusa: Medusa) -> Tuple[bool, Optional[str]]:
    """
    Acquire and save a UV-VIS reference spectrum using pure solvent.

    This function:
    - Transfers pure NMR solvent to the UV-VIS cell.
    - Acquires a reference spectrum for absorbance calculations.
    - Removes the solvent from the UV-VIS cell after acquisition.

    Args:
        medusa (Medusa): Medusa hardware control object.

    Returns:
        Tuple[bool, Optional[str]]: (success, filename)
            - success (bool): True if the reference spectrum was acquired and saved.
            - filename (str or None): Path to the saved reference spectrum file, or None if acquisition failed.

    Side Effects:
        - Controls hardware (liquid transfer, spectrum acquisition).
        - Writes spectrum file to disk.
        - Logs all actions and errors.
    """
    
    try:
        medusa.logger.info("Setting up UV-VIS reference spectrum...")
        
        # Add NMR solvent to UV-VIS cell using proper transfer utility
        to_uv_vis_reference_transfer(medusa)
        
        # Take reference spectrum
        spectrum, wavelengths, filename, _, _ = uv_vis.take_spectrum(reference=True)
        
        if spectrum is not None and wavelengths is not None:
            medusa.logger.info(f"UV-VIS reference spectrum saved: {filename}")
            # Remove NMR solvent from UV-VIS cell using proper transfer utility
            from_uv_vis_cleanup_transfer(medusa, target="NMR_Solvent_Vessel", volume=config.uv_vis_transfer_params.get("volume", 1.5))
            return True, filename

        else:
            medusa.logger.error("Failed to acquire UV-VIS reference spectrum")
            return False, None
            
    except Exception as e:
        medusa.logger.error(f"UV-VIS reference setup failed: {str(e)}")
        return False, None


def setup_uv_vis_t0(medusa: Medusa) -> Tuple[bool, Optional[str]]:
    """
    Acquire and save a UV-VIS t0 spectrum using the reaction mixture.

    This function:
    - Transfers the reaction mixture to the UV-VIS cell.
    - Acquires a t0 spectrum before modification reagent addition.

    Args:
        medusa (Medusa): Medusa hardware control object.

    Returns:
        Tuple[bool, Optional[str]]: (success, filename)
            - success (bool): True if the t0 spectrum was acquired and saved.
            - filename (str or None): Path to the saved t0 spectrum file, or None if acquisition failed.

    Side Effects:
        - Controls hardware (liquid transfer, spectrum acquisition).
        - Writes spectrum file to disk.
        - Logs all actions and errors.
    """

    
    try:
        medusa.logger.info("Setting up UV-VIS t0 spectrum...")
        
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
    Add modification reagent to the reaction vial with hotplate and vial control.

    This function:
    - Sets the hotplate to the modification temperature and rpm.
    - Waits until the hotplate reaches the target temperature.
    - Adds the modification reagent using error-safe transfer.
    - Lowers the reaction vial into the hotplate after reagent addition.

    Args:
        medusa (Medusa): Medusa hardware control object.
        modification_params (dict): Modification parameters from config.

    Returns:
        bool: True if successful, False otherwise.

    Side Effects:
        - Controls hardware (hotplate, actuator, liquid transfer).
        - Logs all actions and errors.
    """

    #set hotplate to modification temperature
    medusa.logger.info(f"Setting hotplate temperature and rpm for modification...")
    medusa.heat_stir(vessel="Reaction_Vial", temperature = config.temperatures.get("modification_temp", 30), rpm = config.set_rpm.get("modification_rpm",400))


    #check if the modification temperature is yet reached at the hotplate
    modification_temp = config.temperatures.get("modification_temp", 30)
    while abs(medusa.get_hotplate_temperature("Reaction_Vial") - modification_temp) > 2:
        time.sleep(30)
        real_temp = medusa.get_hotplate_temperature("Reaction_Vial") 
        medusa.logger.info(f"Hotplate temperature {real_temp} °C is not within +-2°C of target temperature {modification_temp} °C. Waiting...")

    
    


    try:             
        medusa.logger.info("Adding modification reagent...")
        
        # Use error-safe transfer for modification reagent addition
        add_modification_reagent_transfer(medusa)
        
        medusa.logger.info("Modification reagent added successfully")
        # after addition of modification reagent, lower vial into heaptlate
        medusa.logger.info("Lowering reaction vial into hotplate...")
        medusa.write_serial("Linear_Actuator", "1000")       
        return True
        
    except Exception as e:
        medusa.logger.error(f"Modification reagent addition failed: {str(e)}")
        return False


def monitor_modification_reaction(medusa: Medusa, modification_params: Dict) -> Dict:
    """
    Monitor the modification reaction using UV-VIS spectroscopy and absorbance stability.

    This function:
    - Continuously monitors the UV-VIS absorbance of the reaction mixture.
    - Detects reaction completion based on absorbance stability over a set number of measurements.
    - After completion, lifts the vial from the hotplate and sets the hotplate temperature to 0 while stirring.

    Args:
        medusa (Medusa): Medusa hardware control object.
        modification_params (dict): Modification parameters from config.

    Returns:
        dict: Monitoring results including final conversion, measurement count, and completion status.

    Side Effects:
        - Controls hardware (liquid transfer, hotplate, actuator).
        - Writes measurement data to disk.
        - Logs all actions and errors.
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

    #after reaction is over, set hotplate temperature to 0 and continue stirring
    medusa.logger.info("Reaction finished, lifting reaction vial from hotplate and setting temperature on hotplate to 0, while stirring.")
    medusa.heat_stir(vessel="Reaction_Vial",temperature = 0, rpm = config.set_rpm.get("post_modification_rpm",300))
    medusa.write_serial("Linear_Actuator", "2000")
    medusa.logger.info(f"Vial lifted out of hotplate and hotplate temperature set to 0, while stirring at {config.set_rpm.get("post_modification_rpm")}.")


    return {
        'success': True,
        'total_iterations': iteration,
        'final_conversion': final_conversion,
        'reaction_complete': reaction_complete,
        'measurements': measurements
    }




def generate_modification_summary(experiment_id: str, data_base_path: str, 
                                monitoring_results: Dict, modification_params: Dict) -> Dict:
    """
    Generate summary files (TXT and CSV) for the modification workflow.

    This function:
    - Creates detailed text and CSV summary files for the modification workflow.
    - Includes parameters, results, and measurement history.

    Args:
        experiment_id (str): Experiment identifier.
        data_base_path (str): Base path for data storage.
        monitoring_results (dict): Results from modification monitoring.
        modification_params (dict): Modification parameters used.

    Returns:
        dict: Paths to generated summary files (TXT and CSV).

    Side Effects:
        - Writes summary files to disk.
        - Logs all actions and errors.
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
    Run the complete modification workflow, including all hardware and data steps.

    This function orchestrates:
    - Deoxygenation
    - UV-VIS reference and t0 setup
    - Modification reagent addition with hotplate/vial control
    - UV-VIS monitoring with absorbance stability
    - Post-modification dialysis (handled in platform controller)
    - Summary file generation
    - Final argon push to UV/VIS cell

    Args:
        medusa (Medusa): Medusa hardware control object.
        modification_params (dict, optional): Modification parameters (uses config if None).
        experiment_id (str, optional): Experiment identifier (uses config if None).
        data_base_path (str, optional): Base path for data storage (uses config if None).
        uv_vis_data_base_path (str, optional): UV-VIS data path (uses config if None).

    Returns:
        dict: Complete workflow results, including success status, step results, summary files, and error messages.

    Side Effects:
        - Controls hardware (liquid transfer, hotplate, actuator, gas valve).
        - Writes data and summary files to disk.
        - Logs all actions and errors.
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
        
        # Step 8: Push 10 mL of argon to the UV/VIS cell (valve open, safe transfer)
        medusa.logger.info("Step 8: Push 10 mL of argon to the UV/VIS cell (Analytical Pump)")
        try:
            # Open gas valve
            medusa.write_serial("Gas_Valve", "GAS_ON")
            # Push 10 mL of argon from Gas_Reservoir_Vessel to UV_VIS
            from src.liquid_transfers.liquid_transfers_utils import serial_communication_error_safe_transfer_volumetric
            serial_communication_error_safe_transfer_volumetric(
                medusa,
                source="Gas_Reservoir_Vessel",
                target="UV_VIS",
                pump_id="Analytical_Pump",
                volume=10,
                transfer_type="gas",
                draw_speed=0.2,
                dispense_speed=0.05,
            )
            medusa.logger.info("Argon push to UV/VIS cell completed successfully.")
        except Exception as e:
            medusa.logger.error(f"Argon push to UV/VIS cell failed: {str(e)}")
        finally:
            # Always close the gas valve
            medusa.write_serial("Gas_Valve", "GAS_OFF")

        
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
