from re import T
from src.liquid_transfers.liquid_transfers_utils import  (nmr_flush_gas_cleaning, to_nmr_liquid_transfer_cleaning, 
from_nmr_liquid_transfer_cleaning, serial_communication_error_safe_transfer_volumetric, clean_reaction_vial_transfers_to_vial)
import time
import users.config.platform_config as config


#open the gas valve so every transfer afterwards can use the flushing
def open_gas_valve(medusa):
    medusa.logger.info("Opening the gas valve to make flushing possible...")
    medusa.write_serial("Gas_Valve", "GAS_ON")
    medusa.logger.info("Gas valve is opened")

#moving vial into hotplate
def moving_vial(medusa):
    medusa.logger.info("Moving reaction vial into hotplate for cleaning...")
    medusa.write_serial("Linear_Actuator", "1000")

#set rpm for cleaning
def setting_rpm(medusa):
    medusa.logger.info(f"Setting hotplate RPM to {config.set_rpm.get("cleaning_rpm", 300)   }...")
    medusa.heat_stir(vessel="Reaction_Vial", rpm=config.set_rpm.get("cleaning_rpm",300))

#clean the uv_vis cell by flushing clean solvent in there
def clean_uv_vis_cell(medusa, cleaning_params):
    try:
        medusa.logger.info("Starting cleaning of UV/VIS cell...")
        medusa.logger.info("Flushing solvent through the UV_VIS cell to Reaction Vial")
        #pump a few mL of purge solvent to the UV_VIS_cell
        serial_communication_error_safe_transfer_volumetric(medusa, **{
            "source": "Purge_Solvent_Vessel_2", "target": "UV_VIS", "pump_id": "Analytical_Pump",
            "transfer_type": "liquid",
            "volume": config.cleaning_params.get("uv_vis_cleaning_volume", 7), "draw_speed": config.cleaning_params.get("uv_vis_cleaning_draw_speed", 0.08), "dispense_speed": config.cleaning_params.get("duv_vis_cleaning_dispense_speed", 0.05),
            "flush": config.cleaning_params.get("uv_vis_cleaning_flush", 1), "flush_volume": config.cleaning_params.get("uv_vis_cleaning_flush_volume", 5)
        })
        medusa.logger.info("Finished flushing of UV/VIS cell.")
    except Exception as e:
        medusa.logger.warning(f"There was an error: {e}. Please check if the UV/VIS cell is clean before you start the next run.")
    finally: 
        pass

#clean the nmr cell by flushingclean solvent in and out and finally flushing with inert gas
def clean_nmr_cell(medusa):
    try:
        for nmr_cleaning_repetitions in range(config.cleaning_params.get("nmr_cleaning_repetitions",2)):
            medusa.logger.info(f"Starting cycle #{nmr_cleaning_repetitions} for NMR cell cleaning...")
            medusa.logger.info("Flushing purge solvent to the NMR cell...")
            to_nmr_liquid_transfer_cleaning(medusa)
            time.sleep(10) #give a bit of time for mixing and dissolution of impurities in the flow cell
            medusa.logger.info("Finished flushing purge solvent to the NMR cell.")
            medusa.logger.info("Starting drawing purge solvent from the NMR cell...")
            from_nmr_liquid_transfer_cleaning(medusa)
            medusa.logger.info("Finished drawing purge solvent back from the NMR cell and disposing to waste.")
        medusa.logger.info("Starting flushing the NMR cell with inert gas...")
        nmr_flush_gas_cleaning(medusa)
        medusa.logger.info("Finished flushing NMR cell with inert gas.")
    except Exception as e:
        medusa.logger.warning(f"There was an error: {e}. Please check if the NMR cell is clean before you start the next run.")
    finally:
        pass

#orchestrates the cleaning of the reaction vial and dialysis module
def clean_reaction_vial_and_dialysis(medusa):
    try: 
        for reaction_vial_cleaning_repetitions in range(config.cleaning_params.get("reaction_vial_cleaning_repetitions")):
            #dispense clean solvent to reaction vial
            medusa.logger.info(f"Cleaning of reaction vial initialized. Cycle nr. {reaction_vial_cleaning_repetitions}")
            medusa.logger.info("Starting to fill the reaction vial with purge solvent...")
            clean_reaction_vial_transfers_to_vial(medusa)
            medusa.logger.info("Finished filling the reaction vial with purge solvent.")
            #start polymer peristaltic pump to flush 
            medusa.logger.info(f"Starting the polymer peristaltic pumps to clean the polymer dialysis pathway.")
            medusa.transfer_continuous(
                source="Reaction_Vial",
                target="Reaction_Vial",
                pump_id="Polymer_Peri_Pump",
                transfer_rate=1, #rpm
                direction_CW=False
            )
            medusa.logger.info(f"Waiting for {reaction_vial_cleaning_wait_time_sec} sec while peristaltic pump is pumping.")
            #wait for time x to clean vial and flush the polymer path of the dialysis
            reaction_vial_cleaning_wait_time_sec = int(config.cleaning_params.get("reaction_vial_cleaning_wait_time_min"))*60
            time.sleep(reaction_vial_cleaning_wait_time_sec)
            #return the direction of the pump to pump back the cleaning solvent
            medusa.logger.info(f"Changing direction of the polymer peristalic pump to flush all liquid back to the reaction vial.")
            medusa.transfer_continuous(
                source="Reaction_Vial",
                target="Reaction_Vial",
                pump_id="Polymer_Peri_Pump",
                transfer_rate=1,        #rpm
                direction_CW=True
            )
            medusa.logger.info("Waiting for 5 min...")
            #wait for the pump to pump everything back (5 min)
            time.sleep(300)
            medusa.logger.info("Stopping polymer peristaltic pump.")
            #stop the pump
            medusa.transfer_continuous(
                source="Reaction_Vial",
                target="Reaction_Vial",
                pump_id="Polymer_Peri_Pump",
                transfer_rate=0,
                direction_CW=True
            )
            medusa.logger.info("Starting the removal of the cleaning solvent from the reaction vial...")
            #pump everything from the reaction vial to waste
            removal_volume = float(config.cleaning_params.get("cleaning_volume_each_pump"))*4 
            serial_communication_error_safe_transfer_volumetric(
            medusa,
            source="Reaction_Vial", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump",
            transfer_type= "liquid",
            volume=removal_volume, draw_speed=config.cleaning_params.get("dispense_speed_each_pump", 0.3), dispense_speed=config.cleaning_params.get("draw_speed_each_pump", 0.3), #draw speed and dispense speed are the opposite of what they were for the transfer to the reaction vial
            post_rinse_vessel=config.cleaning_params.get("reaction_vial_cleaning_post_rinse_vessel", "Purge_Solvent_Vessel_2"), post_rinse= 1, post_rinse_volume=config.cleaning_params.get("reaction_vial_cleaning_post_rinse_volume", 1.5),
            post_rinse_speed=0.15)
            medusa.logger.info("Finished removal from the reaction vial.")

    except Exception as e:
            medusa.logger.warning(f"There was an error: {e}. Please check if the reaction vial and dialysis module is clean before you start the next run.")
    finally:
        pass

#flushes potentially contaminated solvent from the dialysis module to waste
def purge_eluent_peri_pump(medusa):
    medusa.logger.info("Starting solvent peristaltic pump to purge out dirty solvent from solvent path in dialysis module.")
    medusa.transfer_continuous(
                source="Elution_Solvent_Vessel",
                target="Waste_Vessel",
                pump_id="Solvent_Peri_Pump",
                transfer_rate=1,        #rpm
                direction_CW=True
            )
    medusa.logger.info("Wait for 5 min.")
    #wait for 5 min (should be enough to purge dirty solvent out)        
    time.sleep(300)
    #stop pump
    medusa.logger.info("Stop solvent peristaltic pump.")
    medusa.transfer_continuous(
                source="Elution_Solvent_Vessel",
                target="Waste_Vessel",
                pump_id="Solvent_Peri_Pump",
                transfer_rate=0,        #rpm
                direction_CW=True
            )
    medusa.logger.info("Solvent flowpath in dialysis module was cleaned.")

#drying of the reaction vial by heating and purging inert gas through it
def dry_reaction_vial(medusa):
    try: 
        #heat hotplate to user defined value
        medusa.logger.info(f"Heating reaction vial to {config.temperatures.get("cleaning_dry_temp", 60)} °C to remove the remaining cleaning solvent.")
        medusa.heat_stir(vessel="Reaction_Vial", temperature = config.temperatures.get("cleaning_dry_temp", 60))


        #repeat whole process for user defined time
   
        dry_reaction_vial_wait_sec = float(config.cleaning_params.get("dry_reaction_vial_wait_min"))*60
        medusa.logger.info(f"For {dry_reaction_vial_wait_sec/60} min flush inert gas through the reaction vial with a syringe pump to remove the remaining cleaning solvent.")
        start_time = time.time()
        while time.time() - start_time < dry_reaction_vial_wait_sec:
            serial_communication_error_safe_transfer_volumetric(
                medusa,
                source="Gas_Reservoir_Vessel", 
                target="Reaction_Vial", 
                pump_id="Solvent_Monomer_Modification_Pump", 
                volume=10, draw_speed=0.1, dispense_speed=0.1,
                transfer_type="gas", 
            )
            time.sleep(1)  # wait time for pump to properly reset
        medusa.logger.info("Finished flushing with inert gas through the reaction vial to remove remaining cleaning solvent ")
    except Exception as e:
        medusa.logger.warning(f"There was an error: {e}. Please check if the reaction vial and dialysis module is clean before you start the next run.")
    finally:
        medusa.logger.info("Shutting down the hotplate (setting to 0 °C and 0 rpm).")
        medusa.heat_stir(vessel="Reaction_Vial", temperature = 0, rpm = 0)
        medusa.logger.info("Closing the gas valve.")
        medusa.write_serial("Gas_Valve", "GAS_OFF")



#this function will execute the compounded subfunctions to clean the platform (except the precipitation vial)
def run_cleaning_module(medusa):
    open_gas_valve(medusa)
    clean_uv_vis_cell(medusa)
    clean_nmr_cell(medusa)
    setting_rpm(medusa)
    moving_vial(medusa)
    clean_reaction_vial_and_dialysis(medusa)
    purge_eluent_peri_pump(medusa)
    dry_reaction_vial(medusa)

  
#ToDo: possibly implement also a cleaning step for the Precipitation vessel (but for now we just leave it like that)    











