from src.liquid_transfers.liquid_transfers_utils import serial_communication_error_safe_transfer_volumetric
import time
import users.config.platform_config as config




def add_non_solvent(medusa, precipitation_params):
    #1. step: pump user defined mL of non solvent to precipiation vessel
    #pump x mL of methao
    #precipitation valve already open (in state "PRECIP_OFF") (connection to precipitation pump is open, connection to gas valve is closed)
    medusa.logger.info("Connection from Precipitation_Pump to Precipitation_Vessel (using precipitation_vessel_solenoid) is open")
    medusa.write_serial("Precipitation_Valve","PRECIP_OFF")
    #opening argon valve to make flushing with argon possible
    medusa.logger.info("Opening gas valve to make flushing available...") #opening gas valve to make flushing possible
    medusa.write_serial("Gas_Valve", "GAS_ON")
    medusa.logger.info("Transferring precipitation solvent to Precipitation_Vessel")
    #pump 25 mL of non solvent to the precipitation module
    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Methanol_Vessel", "target": "Precipitation_Vessel_Solenoid", "pump_id": "Precipitation_Pump",
        "transfer_type": "liquid",
        "volume": precipitation_params.get("non_solvent_volume", 25), "draw_speed": precipitation_params.get("non_solvent_draw_speed", 0.08), "dispense_speed": precipitation_params.get("non_solvent_dispense_speed", 0.05),
        "flush": precipitation_params.get("non_solvent_flush", 1), "flush_volume": precipitation_params.get("non_solvent_flush_volume", 5),
        "post_rinse_vessel": precipitation_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": precipitation_params.get("non_solvent_post_rinse", 1), 
        "post_rinse_volume": precipitation_params.get("non_solvent_post_rinse_volume", 2.5), "post_rinse_speed": precipitation_params.get("non_solvent_post_rinse_speed", 0.1)    
    })


def bubble_inert_gas(medusa):
    #2. step: change opened port on precipitation solenoid valve to connect argon line and precipitation vessel
    #opening inert gas valve
    medusa.logger.info("Set gas valve to open state...") #opening gas valve to make flushing possible
    medusa.write_serial("Gas_Valve", "GAS_ON")
    medusa.logger.info("Gas valve opened") #opening gas valve to make flushing possible
    #set solenoid valve to bubble argon through the precipiation solenoid valve
    medusa.logger.info("Changing state of precipitation solenoid valve to inert gas connection...") 
    medusa.write_serial("Precipitation_Valve","PRECIP_ON")
    medusa.logger.info("State change successful") 
    

def transfer_polymer_to_precipitation(medusa, precipitation_params):
    #3. step: transfer polymer to the precipitation vessel
    medusa.logger.info("Transferring polymer from Reaction_Vial to Precipitation_Vessel...")
   #pump user defined amount of polymer to the precipitation vessel (through upper hole)
    serial_communication_error_safe_transfer_volumetric(medusa, **{
        "source": "Reaction_Vial", "target": "Precipitation_Vessel_Dispense", "pump_id": "Precipitation_Pump",
        "transfer_type": "liquid",
        "volume": precipitation_params.get("polymer_volume", 25), "draw_speed": precipitation_params.get("polymer_draw_speed", 0.03), "dispense_speed": precipitation_params.get("polymer_dispense_speed", 0.05),
        "flush": precipitation_params.get("polymer_flush", 1), "flush_volume": precipitation_params.get("polymer_flush_volume", 5),
        "post_rinse_vessel": precipitation_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": precipitation_params.get("polymer_post_rinse", 1), 
        "post_rinse_volume": precipitation_params.get("polymer_post_rinse_volume", 5), "post_rinse_speed": precipitation_params.get("polymer_post_rinse_speed", 0.1)    
    })
    medusa.logger.info("Transfer of polymer from Reaction_Vial to Precipitation_Vessel finished")

def mix_while_bubbling (medusa, precipitation_wait_sec, pump_id="Precipitation_Pump", ):
    #4. step pump argon through the solution to mix everything well
    try:
        medusa.logger.info(f"Starting mixing by sparging inert gas through the solution in the Precipitation_Vessel for {precipitation_wait_sec} seconds using pump {pump_id}...")
        
        #open gas valve to sparge inert gas to the precipitation valve
        medusa.logger.info("Set gas valve to open state...") #opening inert gas valve to flush argon from the bottom of the precipitation vessel through it
        medusa.write_serial("Gas_Valve", "GAS_ON")
        medusa.logger.info("Gas valve opened") #opening gas valve to make flushing possible
        #ensure that precipitation valve is also opened
        medusa.write_serial("Precipitation_Valve","PRECIP_ON")


        # Active mixing by argon sparging
        start_time = time.time()
        while time.time() - start_time < precipitation_wait_sec:
            serial_communication_error_safe_transfer_volumetric(
                medusa,
                source="Gas_Reservoir_Vessel", 
                target="Precipitation_Vessel_Dispense", 
                pump_id=pump_id, 
                volume=10, draw_speed=0.25, dispense_speed=0.25,
                transfer_type="gas", 
                flush=1, flush_speed=0.25, flush_volume=10,
            )
            time.sleep(1)  # wait time for pump to properly reset
        medusa.logger.info(f"Finished mixing by sparging inert gas through the solution in the Precipitation_Vessel")
    except Exception as e:
        medusa.logger.error(f"An error occured: {str(e)}")
        try:
            medusa.write_serial("Gas_Valve", "GAS_OFF") #close gas valve to prevent inert gas waste
            medusa.write_serial("Precipitation_Valve", "PRECIP_OFF") #prevent fluid from leaking into the the gas line due to backpressure
        except:
            pass
        return False

def remove_supernatant(medusa, precipitation_params):
    #5. step: draw from bottom port of precipitation vessel to waste

    #change position of precipitation valve to the correct one for connection of the precipitation pump with the precipitation vessel
    medusa.logger.info("Changing state of precipitation solenoid valve to Precipitation_Pump connection...") 
    medusa.write_serial("Precipitation_Valve","PRECIP_OFF")
    medusa.logger.info("State changed. Connection from Precipitation_Pump to Precipitation_Vessel (using precipitation_vessel_solenoid) is open")
    #draw same amount of precipitation solvent as before (+5 mL) from the precipitation vessel 
    try:        
        #change variable for volume to remove 5 mL more than were originally added in form of non solvent
        non_solvent_volume = precipitation_params.get("non_solvent_volume", None)
        removal_volume = int(non_solvent_volume) + 5 if non_solvent_volume is not None else precipitation_params.get("non_solvent_volume", 25)
        medusa.logger.info(f"Removing {removal_volume} mL from the precipitation vessel")
        #draw removal_volume from the precipitation valve and put to waste  
        serial_communication_error_safe_transfer_volumetric(medusa, **{
            "source": "Precipitation_Vessel_Solenoid", "target": "Waste_Vessel", "pump_id": "Precipitation_Pump",
            "transfer_type": "liquid",
            "volume": removal_volume, "draw_speed": precipitation_params.get("remove_supernatant_draw_speed", 0.08), "dispense_speed": precipitation_params.get("remove_supernatant_dispense_speed", 0.05),
            "post_rinse_vessel": precipitation_params.get("post_rinse_vessel", "Purge_Solvent_Vessel_1"), "post_rinse": precipitation_params.get("remove_supernatant_post_rinse", 1), 
            "post_rinse_volume": precipitation_params.get("remove_supernatant_post_rinse_volume", 2.5), "post_rinse_speed": precipitation_params.get("remove_supernatant_post_rinse_speed", 0.1)    
    })
    except Exception as e:
        medusa.logger.error(f"An error occured: {str(e)}")
        try:
            medusa.write_serial("Gas_Valve", "GAS_OFF") #close gas valve to prevent inert gas waste
            medusa.write_serial("Precipitation_Valve", "PRECIP_OFF") #prevent fluid from leaking into the the gas line due to backpressure
        except:
            pass
        return False

def dry_polymer(medusa): 
    #6. step: drying the polymer by sparging argon from top and bottom of the precipitation vessel
        
    drying_wait_minutes = config.precipitation_params.get{"drying_wait_minutes", 0}
    drying_wait_seconds = float(drying_wait_minutes) *60
    try:
        medusa.logger.info(f"Start drying of the polymer for {drying_wait_minutes} minutes...")

        #change position of precipitation valve to the correct one for connection of the gas valve with the precipitation vessel
        medusa.logger.info("Changing state of precipitation solenoid valve to gas valve connection...") 
        medusa.write_serial("Precipitation_Valve","PRECIP_ON")
        medusa.logger.info("State changed. Connection from Precipitation_Pump to Precipitation_Vessel (using precipitation_vessel_solenoid) is open")

        #opening inert gas valve
        medusa.logger.info("Set gas valve to open state...") #opening inert gas valve to flush argon from the bottom of the precipitation vessel through it
        medusa.write_serial("Gas_Valve", "GAS_ON")
        medusa.logger.info("Gas valve opened") #opening gas valve to make flushing possible

        # Active mixing by argon sparging
        start_time = time.time()
        while time.time() - start_time < drying_wait_seconds:
                serial_communication_error_safe_transfer_volumetric(
                    medusa,
                    source="Gas_Reservoir_Vessel", 
                    target="Precipitation_Vessel_Dispense", 
                    pump_id="Precipitation_Pump", 
                    volume=10, draw_speed=0.5, dispense_speed=0.5,
                    transfer_type="gas", 
                    flush=1, flush_speed=0.25, flush_volume=10,
                )
                time.sleep(1)  # wait time for pump to properly reset
        medusa.logger.info(f"Finished drying of polymer for {drying_wait_minutes} minutes.")
    except Exception as e:
            medusa.logger.error(f"An error occured: {str(e)}")
            try:
                medusa.write_serial("Gas_Valve", "GAS_OFF") #close gas valve to prevent inert gas waste
                medusa.write_serial("Precipitation_Valve", "PRECIP_OFF") #prevent fluid from leaking into the the gas line due to backpressure
            except:
                pass
            return False

def close_all_valves(medusa):
    #closing inert gas valve
    medusa.logger.info("Set gas valve to closed state...") #opening gas valve to make flushing possible
    medusa.write_serial("Gas_Valve", "GAS_OFF")
    medusa.logger.info("Gas valve closed") #opening gas valve to make flushing possible
    #set solenoid valve to bubble argon through the precipiation solenoid valve
    medusa.logger.info("Setting state of precipitation solenoid valve to pump connection...") 
    medusa.write_serial("Precipitation_Valve","PRECIP_OFF")
    medusa.logger.info("Setting state successful") 


def run_precipitation_workflow(medusa, precipitation_wait_sec,  precipitation_params):
        
    washing_steps = config.precipitation_params.get("washing_cycles",0)
        
    add_non_solvent(medusa, precipitation_params)
    bubble_inert_gas(medusa)
    transfer_polymer_to_precipitation(medusa, precipitation_params)
    mix_while_bubbling (medusa, precipitation_wait_sec, pump_id="Precipitation_Pump", )
    remove_supernatant(medusa, precipitation_params)
    for step in range(washing_steps-1):
        medusa.logger.info(f"Start of washing step {step + 1}.")
        add_non_solvent(medusa, precipitation_params)
        mix_while_bubbling (medusa, precipitation_wait_sec, pump_id="Precipitation_Pump", )
        remove_supernatant(medusa, precipitation_params)
        medusa.logger.info(f"End of washing step {step + 1}.")
    dry_polymer(medusa, precipitation_params)