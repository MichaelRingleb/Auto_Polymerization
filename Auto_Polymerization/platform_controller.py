"""
Auto_Polymerization Platform Controller

This module serves as the main orchestrator for the complete Auto_Polymerization workflow.
It coordinates all workflow steps including preparation, polymerization, monitoring, 
dialysis, modification, and post-modification dialysis.

The platform controller manages:
- Hardware initialization and configuration
- Workflow step execution and error handling
- Data flow between workflow modules
- Logging and status reporting
- Configuration management

Workflow Steps:
1. Preparation: Hardware setup, priming, and NMR shimming
2. Polymerization: Component transfer, deoxygenation, and reaction initiation
3. Monitoring: NMR-based polymerization progress tracking
4. Dialysis: Polymer purification using peristaltic pumps
5. Modification: UV-VIS-based functionalization reaction
6. Post-modification dialysis: Additional purification after modification

Dependencies:
- medusa: Hardware control framework
- matterlab_spectrometers: Spectroscopy control
- src.workflow_steps.*: Individual workflow modules
- users.config.platform_config: Configuration parameters

Author: Michael Ringleb (with help from cursor.ai)
Date: [Current Date]
Version: 1.0
"""

from re import M
import sys
import os
import logging
from pathlib import Path
from medusa import Medusa, MedusaDesigner
import time
import matterlab_spectrometers as spectrometer
import src.UV_VIS.uv_vis_utils as uv_vis
import src.NMR.nmr_utils as nmr_utils

# Import user-editable platform configuration
import users.config.platform_config as config

# Import workflow step modules
from src.workflow_steps._0_preparation import run_preparation_workflow
from src.workflow_steps._1_polymerization_module import run_polymerization_workflow
from src.workflow_steps._2_polymerization_monitoring import run_polymerization_monitoring
from src.workflow_steps._3_dialysis_module import run_dialysis_workflow
from src.workflow_steps._4_modification_module import run_modification_workflow
from src.workflow_steps._5_precipitation_module import run_precipitation_workflow
from src.workflow_steps._6_cleaning_module import run_cleaning_workflow


def find_layout_json(config_folder='Auto_Polymerization/users/config/'):
    """
    Search for the first .json file in the config folder and return its path.
    
    This function automatically discovers the Medusa layout configuration file
    that defines the hardware connections and vessel configurations.
    
    Args:
        config_folder (str): Path to the configuration folder containing layout files
        
    Returns:
        str: Full path to the first .json layout file found
        
    Raises:
        FileNotFoundError: If no .json file is found in the config folder
    """
    for fname in os.listdir(config_folder):
        if fname.endswith('.json'):
            layout = os.path.join(config_folder, fname)
            print(f"Found layout JSON: {layout}")
            return layout
    raise FileNotFoundError("No .json file found in the config folder.")


def main():
    """
    Main platform controller function that executes the complete Auto_Polymerization workflow.
    
    This function orchestrates the entire polymerization process from preparation
    through final modification. It handles hardware initialization, workflow
    execution, error handling, and result reporting.
    
    Workflow Sequence:
    1. Preparation: Hardware setup and NMR shimming
    2. Polymerization: Component transfer and reaction initiation
    3. Monitoring: NMR-based progress tracking
    4. Dialysis: Polymer purification
    5. Modification: UV-VIS-based functionalization
    6. Post-modification dialysis: Additional purification
    
    Returns:
        None: Exits on workflow completion or error
        
    Raises:
        Various exceptions from workflow modules are caught and logged
    """
    
    # Setup logging for Medusa liquid transfers
    logger = logging.getLogger("platform_controller")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    # Instantiate Medusa object with layout configuration
    layout = find_layout_json() 
    medusa = Medusa(
        graph_layout=Path(layout),
        logger=logger     
    )
    
    medusa.logger.info(f"Starting Auto_Polymerization experiment: {config.experiment_id}")
    
    # Step 0: Preparation workflow - Hardware setup and NMR shimming
    medusa.logger.info("Step 0: Running preparation workflow...")
    try:
        run_preparation_workflow(
            medusa=medusa,
            polymerization_temp=config.temperatures.get("polymerization_temp", 20),
            set_rpm=config.target_rpm.get("polymerization_rpm", 600),
            prime_transfer_params=config.prime_transfer_params,
            run_minimal_test=config.run_minimal_workflow_test  # Set to True in config to run minimal workflow test
        )
        medusa.logger.info("Preparation workflow completed successfully.")
    except Exception as e:
        medusa.logger.error(f"Preparation workflow failed: {str(e)}")
        return
    
    # Step 1: Polymerization with pre-polymerization setup
    medusa.logger.info("Step 1: Running polymerization workflow with pre-polymerization setup...")
    polymerization_result = run_polymerization_workflow(
        medusa=medusa,
        polymerization_params=config.polymerization_params,
        polymerization_temp=config.temperatures["polymerization_temp"],
        set_rpm=config.target_rpm["polymerization_rpm"],
        deoxygenation_time=config.polymerization_params.get("deoxygenation_time", 300),
        monitoring_params=config.polymerization_monitoring_params,  # Pass monitoring params for t0 measurements
        experiment_id=config.experiment_id,
        nmr_data_base_path=config.nmr_data_base_path
    )
    
    if not polymerization_result['success']:
        medusa.logger.error(f"Polymerization workflow failed: {polymerization_result['error_message']}")
        return
    
    medusa.logger.info("Polymerization workflow completed successfully.")
    
    # Extract t0 baseline data for monitoring
    t0_baseline = polymerization_result.get('t0_baseline')
    if t0_baseline and t0_baseline['success']:
        medusa.logger.info(f"t0 baseline established: {t0_baseline['successful_count']}/{t0_baseline['total_count']} successful measurements")
    else:
        medusa.logger.warning("No valid t0 baseline available for monitoring")
    
    # Step 2: Polymerization monitoring - Track reaction progress via NMR
    medusa.logger.info("Step 2: Running polymerization monitoring...")
    monitoring_result = run_polymerization_monitoring(
        medusa=medusa,
        monitoring_params=config.polymerization_monitoring_params,
        experiment_id=config.experiment_id,
        t0_baseline=t0_baseline,  # Pass t0 baseline data
        nmr_data_base_path=config.nmr_data_base_path,
        data_base_path=config.data_base_path
    )
    
    if not monitoring_result['success']:
        medusa.logger.error("Polymerization monitoring failed")
        return
    
    medusa.logger.info("Polymerization monitoring completed successfully.")
    medusa.logger.info(f"Final conversion: {monitoring_result['final_conversion']:.2f}%")
    medusa.logger.info(f"Total measurements: {monitoring_result['total_measurements']}")
    medusa.logger.info(f"Successful measurements: {monitoring_result['successful_measurements']}")
    medusa.logger.info(f"Summary file: {monitoring_result['summary_file']}")
    
    # Step 3: Dialysis workflow - Polymer purification
    # --- USER-CONFIGURABLE DIALYSIS STOPPING OPTIONS ---
    # Set to True to use NMR noise signal for stopping dialysis
    use_noise_comparison_based_stopping = True
    # Set to True to use time-based stopping for dialysis
    use_time_based_stopping = True
    
    # Update config for dialysis workflow
    config.dialysis_params["noise_comparison_based"] = use_noise_comparison_based_stopping
    config.dialysis_params["time_based"] = use_time_based_stopping

    medusa.logger.info("Step 3: Running dialysis workflow...")
    try:
        dialysis_result = run_dialysis_workflow(medusa)
        medusa.logger.info(f"Dialysis workflow completed. Summary: {dialysis_result.get('summary_txt', 'N/A')}")
    except Exception as e:
        medusa.logger.error(f"Dialysis workflow failed: {str(e)}")
        return
    
    # Step 4: Modification workflow - UV-VIS-based functionalization
    medusa.logger.info("Step 4: Running modification workflow...")
    try:
        modification_result = run_modification_workflow(
            medusa=medusa,
            modification_params=config.modification_params,
            experiment_id=config.experiment_id,
            data_base_path=config.data_base_path,
            uv_vis_data_base_path=config.uv_vis_data_base_path
        )
        
        if not modification_result['success']:
            medusa.logger.error(f"Modification workflow failed: {modification_result.get('error_message', 'Unknown error')}")
            return
        
        medusa.logger.info("Modification workflow completed successfully.")
        medusa.logger.info(f"Final conversion: {modification_result.get('final_conversion', 'N/A')}%")
        medusa.logger.info(f"Total iterations: {modification_result.get('total_iterations', 'N/A')}")
        
        summary_files = modification_result.get('summary_files', {})
        if summary_files.get('summary_txt'):
            medusa.logger.info(f"Summary file: {summary_files['summary_txt']}")
        if summary_files.get('summary_csv'):
            medusa.logger.info(f"CSV file: {summary_files['summary_csv']}")
            
    except Exception as e:
        medusa.logger.error(f"Modification workflow failed: {str(e)}")
        return
    
    # Step 4b: Post-modification dialysis - Additional purification after modification
    medusa.logger.info("Step 4b: Running post-modification dialysis...")
    try:
        # Configure dialysis for time-based stopping only (noise-based disabled)
        original_dialysis_params = config.dialysis_params.copy()
        config.dialysis_params["noise_comparison_based"] = False
        config.dialysis_params["time_based"] = True
        config.dialysis_params["dialysis_duration_mins"] = config.modification_params.get("post_modification_dialysis_hours", 5) * 60
        
        post_dialysis_result = run_dialysis_workflow(medusa)
        medusa.logger.info(f"Post-modification dialysis completed. Summary: {post_dialysis_result.get('summary_txt', 'N/A')}")
        
        # Restore original dialysis parameters
        config.dialysis_params = original_dialysis_params
        
    except Exception as e:
        medusa.logger.error(f"Post-modification dialysis failed: {str(e)}")
        # Restore original dialysis parameters even on failure
        config.dialysis_params = original_dialysis_params
        return
    

    # Step 5: Precipitation workflow
    try:
      medusa.logger.info("Step 5: Precipitation workflow started.")
      run_precipitation_workflow(
        medusa = medusa,
      precipitation_wait_seconds = config.precipitation_params.get("precipitation_wait_sec", 600),  
      precipitation_params =   config.precipitation_params
      )
      medusa.logger.info("Precipitation workflow finished successfully.")
    except Exception as e:
        medusa.logger.error(f"Precipitation workflow failed: {str(e)}")
        return

    # Step 6: Cleaning the setup (flushing with Purge_solvent)
    cleaning_ok = ""

    while cleaning_ok not in ("Y", "N"):
      cleaning_ok = input("Please confirm that cleaning should be executed: Type in Y for yes or N for no! ").strip().upper()
    if cleaning_ok == "Y":
        try:
            medusa.logger.info("Step 6: Cleaning the platform started.")
            run_cleaning_workflow(
                medusa=medusa,
                precipitation_wait_seconds=config.precipitation_params.get("precipitation_wait_sec", 600),
                cleaning_params=config.cleaning_params
            )
            medusa.logger.info("Cleaning workflow finished successfully.")
        except Exception as e:
            medusa.logger.error(f"Cleaning workflow failed: {str(e)}")
    elif cleaning_ok == "N":
        medusa.logger.info("You decided not to clean the platform automatically. Please make sure it is manually cleaned before you continue using it.")
        exit()
    else:
        medusa.logger.warning("Invalid input received. Please enter Y or N.")





    # Step 6: Cleaning (placeholder for future implementation)
    medusa.logger.info("Step 6: Cleaning workflow (placeholder)")
    # TODO: Implement cleaning workflow
    # from src.workflow_steps._5_cleaning_module import run_cleaning_workflow
    # cleaning_result = run_cleaning_workflow(medusa, cleaning_params, experiment_id, base_path)
    
    medusa.logger.info(f"Auto_Polymerization experiment {config.experiment_id} completed successfully!")







     


#ready for next run
    # Initialize medusa (this would be done by the actual platform)
    # For now, we'll assume medusa is available
    medusa = None  # Placeholder for actual medusa instance







if __name__ == "__main__":
  main()