from src.liquid_transfers.liquid_transfers_utils import serial_communication_error_safe_transfer_volumetric
import time
import users.config.platform_config as config



def open_gas_valve(medusa):
    medusa.logger.info("Opening the gas valve to make flushing possible...")
    medusa.write_serial("Gas_Valve", "GAS_ON")
    medusa.logger.info("Gas valve is opened")


 medusa.logger.info("Moving reaction vial out of heatplate...")
    medusa.write_serial("Linear_Actuator", "2000")
    medusa.logger.info(f"Preheating heatplate to {polymerization_temp}°C and setting RPM to {set_rpm}...")
    medusa.heat_stir(vessel="Reaction_Vial", temperature=polymerization_temp, rpm=set_rpm)

def clean_uv_vis_cell(medusa, cleaning_params):
    medusa.logger.info("Starting cleaning of UV/VIS cell...")






 
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


























def run_cleaning_workflow(medusa, cleaning_params, experiment_id, base_path):
    medusa.logger.info("Starting cleaning workflow...")
    open_gas_valve(medusa)
    flush_reaction_vial_with_solvent(medusa, cleaning_params)
    flush_transfer_lines(medusa, cleaning_params)
    rinse_precipitation_module(medusa, cleaning_params)
    clean_uv_vis_cell(medusa, cleaning_params)
    clean_nmr_probe(medusa, cleaning_params)
    final_purge_with_gas(medusa, cleaning_params)

    logger.info("Cleaning workflow completed successfully.")
    return {"success": True}