"""
Platform controller for the Auto_Polymerization workflow.
Coordinates all workflow steps and manages the complete polymerization process.
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

#imports the different workflow steps from the modules in the workflow_steps folder 
from src.workflow_steps._0_preparation import run_preparation_workflow
from src.workflow_steps._1_polymerization_module import run_polymerization_workflow
from src.workflow_steps._2_polymerization_monitoring import run_polymerization_monitoring
from src.workflow_steps._3_dialysis_module import run_dialysis_workflow


def find_layout_json(config_folder='Auto_Polymerization/users/config/'):
    """
    Search for the first .json file in the config folder and return its path.
    Raises FileNotFoundError if no .json file is found.
    """
    for fname in os.listdir(config_folder):
        if fname.endswith('.json'):
            layout = os.path.join(config_folder, fname)
            print(f"Found layout JSON: {layout}")
            return layout
    raise FileNotFoundError("No .json file found in the config folder.")


def main():
    """
    Main platform controller function.
    Executes the complete Auto_Polymerization workflow.
    """

    #Setup logging for Medusa liquid transfers
    logger = logging.getLogger("platform_controller")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


    #Instantiate Medusa object
    layout = find_layout_json() 
    medusa = Medusa(
        graph_layout=Path(layout),
        logger=logger     
    )
    

    medusa.logger.info(f"Starting Auto_Polymerization experiment: {config.experiment_id}")
    
    # Step 0: Preparation workflow
    medusa.logger.info("Step 0: Running preparation workflow...")
    try:
        run_preparation_workflow(
            medusa=medusa,
            polymerization_temp=config.temperatures.get("polymerization_temp",20),
            set_rpm=config.target_rpm.get("polymerization_rpm",600),
            prime_transfer_params=config.prime_transfer_params,
            run_minimal_test=False  # Set to True to run minimal workflow test
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
    
    # Step 2: Polymerization monitoring
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
    


    # --- USER-CONFIGURABLE DIALYSIS STOPPING OPTIONS ---
    # Set to True to use NMR noise signal for stopping dialysis
    use_noise_comparison_based_stopping = True
    # Set to True to use time-based stopping for dialysis
    use_time_based_stopping = True
    # Maximum dialysis duration in minutes (only relevant if time-based is enabled)
    max_dialysis_time_minutes = 180

    # Update config for dialysis workflow
    config.dialysis_params["noise_comparison_based"] = use_noise_comparison_based_stopping
    config.dialysis_params["time_based"] = use_time_based_stopping
    config.dialysis_params["dialysis_duration_mins"] = max_dialysis_time_minutes

    # Step 3: Dialysis workflow
    medusa.logger.info("Step 3: Running dialysis workflow...")
    try:
        dialysis_result = run_dialysis_workflow(medusa)
        medusa.logger.info(f"Dialysis workflow completed. Summary: {dialysis_result.get('summary_txt', 'N/A')}")
    except Exception as e:
        medusa.logger.error(f"Dialysis workflow failed: {str(e)}")
        return


    
    # Step 4: Modification (placeholder for future implementation)
    medusa.logger.info("Step 4: Modification workflow (placeholder)")
    # TODO: Implement modification workflow
    # from src.workflow_steps._3_modification_module import run_modification_workflow
    # modification_result = run_modification_workflow(medusa, modification_params, experiment_id, base_path)
    
    # Step 5: Precipitation (placeholder for future implementation)
    logger.info("Step 5: Precipitation workflow (placeholder)")
    # TODO: Implement precipitation workflow
    # from src.workflow_steps._4_precipitation_module import run_precipitation_workflow
    # precipitation_result = run_precipitation_workflow(medusa, precipitation_params, experiment_id, base_path)
    
    # Step 6: Cleaning (placeholder for future implementation)
    logger.info("Step 6: Cleaning workflow (placeholder)")
    # TODO: Implement cleaning workflow
    # from src.workflow_steps._5_cleaning_module import run_cleaning_workflow
    # cleaning_result = run_cleaning_workflow(medusa, cleaning_params, experiment_id, base_path)
    
    logger.info(f"Auto_Polymerization experiment {config.experiment_id} completed successfully!")
















#add functionalization step
#degas reaction vial
medusa.write_serial("COM12","GAS_ON")
#degas for 10 min (repeat step below for 10 min)
while timing < 600:
    medusa.transfer_volumetric(source="Gas_Reservoir_Vessel", target="Reaction_Vial", pump_id="Solvent_Monomer_Modification_Pump", volume= 10, transfer_type="liquid", flush=3, dispense_speed=0.1)
    timing += 1
medusa.write_serial("COM12","GAS_OFF")


#add NMR solvent to the UV_VIS cell
medusa.transfer_volumetric(source="NMR_Solvent_Vessel", target="UV_VIS", pump_id="Analytical_Pump", volume= default_volumes.get(1), transfer_type="liquid", draw_speed=draw_speeds.get("uv_vis", 1.2), dispense_speed=dispense_speeds.get("uv_vis", 0.05))

#first measurement of UV_VIS and use this as the reference spectrum
uv_vis.take_spectrum(reference=True)

#remove NMR solvent from UV_VIS cell
medusa.transfer_volumetric(source="UV_VIS", target="NMR_Solvent_Vessel", pump_id="Analytical_Pump", volume = 3, transfer_type="liquid",  draw_speed= draw_speeds.get("uv_vis", 1), dispense_speed=dispense_speeds.get("uv_vis", 4))

#start flow through UV_VIS and measure the t0 spectrum
#flow will go on until stopped by other command (use of async or threading)
medusa.transfer_volumetric(source="Reaction_Vial", target="UV_VIS", pump_id="Analytical_Pump", volume= 2, transfer_type="liquid", draw_speed=Functionalization_draw_speed, dispense_speed=1)
uv_vis.take_spectrum(t0=True)


#add functionalization reagent and flush into reaction vial
medusa.transfer_volumetric(source="Modification_Vessel", target="Reaction_Vial", pump_id="Functionalization_Pump", volume= Functionanilzation_volume, transfer_type="liquid", flush=3, draw_speed=Functionalization_draw_speed, dispense_speed=2)

#take UV_VIS measurement and calculate conversion
spectrum, wavelengths, filename, conversion, reaction_complete = uv_vis.take_spectrum(calculate_conversion=True)

# Monitor functionalization reaction until completion
functionalization_iteration = 0
max_functionalization_iterations = 200  # 10 hours maximum (3 min intervals)

while not reaction_complete and functionalization_iteration < max_functionalization_iterations:
    medusa.transfer_volumetric(source="Reaction_Vial", target="UV_VIS", pump_id="Analytical_Pump", volume= 2, transfer_type="liquid", draw_speed=Functionalization_draw_speed, dispense_speed=1)
    functionalization_iteration += 1
    medusa.logger.info(f"Functionalization monitoring iteration {functionalization_iteration}/{max_functionalization_iterations}")
    
    if conversion is not None:
        medusa.logger.info(f"Current conversion: {conversion:.2f}%")
    
    if reaction_complete:
        medusa.logger.info("Functionalization reaction completed based on absorbance stability")
        break
    
    # Wait before next measurement
    medusa.logger.info("Waiting 3 minutes before next measurement...")
    time.sleep(180)  # 3 minutes
    
    # Take next UV_VIS measurement and calculate conversion
    spectrum, wavelengths, filename, conversion, reaction_complete = uv_vis.take_spectrum(calculate_conversion=True)


if functionalization_iteration >= max_functionalization_iterations:
    medusa.logger.warning(f"Functionalization monitoring stopped after {max_functionalization_iterations} iterations")
    if conversion is not None:
        medusa.logger.info(f"Final conversion achieved: {conversion:.2f}%")
else:
    medusa.logger.info(f"Functionalization completed successfully in {functionalization_iteration} iterations")
    if conversion is not None:
        medusa.logger.info(f"Final conversion: {conversion:.2f}%")


#once functionalization is finished: 

    #open gas valve and pump 10 mL of argon to reaction vial through the UV_VIS cell
medusa.write_serial("COM12","GAS_ON")
medusa.transfer_volumetric(source="Gas_Reservoir_Vessel", target="UV_VIS", pump_id="Analytical_Pump", volume= 10, transfer_type="gas", dispense_speed=10, flush=3)
    #close gas valve
medusa.write_serial("COM12","GAS_OFF")

#another round of dialysis (with peristaltic pumps)
# Start peristaltic pumps   
medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW = False, transfer_rate=0.7)
medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW = True, transfer_rate=0.7)
#wait for 5 h 
time.sleep(18000)
# pump peristaltic pump tubing empty for polymer pump in different direction and stop eluent pump
medusa.transfer_continuous(source="Reaction_Vial", target="Waste_Vessel", pump_id="Polymer_Peri_Pump", direction_CW = True, transfer_rate=0.7)
medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW = False, transfer_rate=0)
    #wait for 10 min to pump fully empty
time.sleep(600)
    #turn off polymer pump
medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Polymer_Peri_Pump", direction_CW = False, transfer_rate=0)


#pump 25 mL of methanol to the precipitation module
 #set solenoid valve accordingly
medusa.write_serial("COM12","PRECIP_ON")
 #pump 25 mL of methanol to the precipitation module
medusa.transfer_volumetric(source="Methanol_Vessel", target="Precipitation_Vessel_Solenoid", pump_id="Precipitation_Pump", volume= 25, transfer_type="liquid", flush=3)
 #close solenoid valve and open gas valve to bubble argon through bottom
medusa.write_serial("COM12","PRECIP_OFF")
medusa.write_serial("COM12","GAS_ON")

#add the polymer to the precipitation vessels upper port
medusa.transfer_volumetric(source="Reaction_Vial", target="Precipitation_Vessel_Dispense", pump_id="Precipitation_Pump", volume= 25, transfer_type="liquid", draw_speed=10, dispense_speed=5, flush=3)
medusa.write_serial("COM12","GAS_OFF")
#wait for some minutes while bubbling (5 min)
time.sleep(300)

#remove supernatant from precipitation vessel
medusa.write_serial("COM12","PRECIP_ON")
medusa.transfer_volumetric(source="Precipitation_Vessel_Solenoid", target="Waste_Vessel", pump_id="Precipitation_Pump", volume= 30, transfer_type="liquid", draw_speed=10, dispense_speed=20)
#
#wash the polymer with methanol
medusa.write_serial("COM12","GAS_ON")
medusa.transfer_volumetric(source="Methanol_Vessel", target="Precipitation_Vessel_Solenoid", pump_id="Precipitation_Pump", volume= 25, transfer_type="liquid", flush=3)
medusa.write_serial("COM12","GAS_OFF")
#change solenoid position to bubble gas through bottom
medusa.write_serial("COM12","PRECIP_OFF")

#remove the supernatant from the precipitation vessel
medusa.write_serial("COM12","PRECIP_ON")
medusa.transfer_volumetric(source="Precipitation_Vessel_Solenoid", target="Waste_Vessel", pump_id="Precipitation_Pump", volume= 30, transfer_type="liquid", draw_speed=10, dispense_speed=20)
medusa.write_serial("COM12","PRECIP_OFF")
#dry polymer by purging argon trhough it from below and above
medusa.write_serial("COM12","GAS_ON")
medusa.transfer_volumetric(source="Gas_Reservoir_Vessel", target="Precipitation_Vessel_Dispense", pump_id="Precipitation_Pump", volume= 100, dispense_speed=25, transfer_type="gas", flush=3)




#clean everything each way from the pumps to the reaction vial, uv_vis and dialysis module before next run
  #open gas valve
medusa.write_serial("COM12","GAS_ON")	
medusa.heat_stir("Reaction_Vial", temperature= 20, rpm= 300)
  #flush the UV_VIS cell
medusa.transfer_volumetric(source="Purge_Solvent_Vessel_2", target="UV_VIS", pump_id="Analytical_Pump", volume= 30, transfer_type="liquid", flush=3, draw_speed=10, dispense_speed=3)
  #flush purge solvent to the waste vessel
medusa.transfer_volumetric(source="UV_VIS", target="Waste_Vessel", pump_id="Analytical_Pump", volume= 5, transfer_type="liquid", flush=3, draw_speed=3, dispense_speed=10)
  #also remove solvent from reaction vial
medusa.transfer_volumetric(source="Reaction_Vial", target="Waste_Vessel", pump_id="Analytical_Pump", volume= 30, transfer_type="liquid", flush=3)
  #flush the Solvent_Monomer_Modification_Pump flowpath
medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Reaction_Vial", pump_id="Solvent_Monomer_Modification_Pump", volume= 20, transfer_type="liquid", flush=3)
  #flush purge solvent to the waste vessel
medusa.transfer_volumetric(source="Reaction_Vial", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= 30, transfer_type="liquid", flush=3)
   #flush the Precipitation_Pump flowpath
medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Reaction_Vial", pump_id="Precipitation_Pump", volume= 20, transfer_type="liquid", flush=3)
  #flush purge solvent to the waste vessel
medusa.transfer_volumetric(source="Reaction_Vial", target="Waste_Vessel", pump_id="Precipitation_Pump", volume= 30, transfer_type="liquid", flush=3)
  #fill reaction_vial with purge solvent
medusa.transfer_volumetric(source="Purge_Solvent_Vessel_1", target="Reaction_Vial", pump_id="Initiator_CTA_Pump", volume= 20, transfer_type="liquid", flush=3)
  #flush purge solvent to the waste vessel
medusa.transfer_volumetric(source="Reaction_Vial", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= 30, transfer_type="liquid", flush=3)
  #close gas valve
medusa.write_serial("COM12","GAS_OFF")
  #dry the reaction vial
medusa.heat_stir("Reaction_Vial", temperature= 80, rpm= 0)
  #wait until vial is at 80 °C (get property)
  #pump 200 mL of argon to dry rest of vial
medusa.transfer_volumetric(source="Gas_Reservoir_Vessel", target="Reaction_Vial", pump_id="Precipitation_Pump", volume= 200, dispense_speed=25, transfer_type="gas", flush=3)
  #get temperature of heatplate
  #let heatplate cool down
medusa.heat_stir("Reaction_Vial", temperature= 25, rpm= 0)
  #wait until heatplate is at 25 °C (get property)
  #close gas valve
medusa.write_serial("COM12","GAS_OFF")


#ready for next run
    # Initialize medusa (this would be done by the actual platform)
    # For now, we'll assume medusa is available
    medusa = None  # Placeholder for actual medusa instance







if __name__ == "__main__":
  main()












