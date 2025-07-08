#central unit to put together individual workflow steps into a complete workflow

#imports the different workflow steps from the modules in the workflow_steps folder 





"""
import yaml
import os

base_dir = os.path.dirname(__file__)
config_path = os.path.join(base_dir, "config.yaml")

with open(config_path, "r") as f:
    config = yaml.safe_load(f)
"""
from re import M
import sys
import os
import logging
from pathlib import Path
from medusa import Medusa, MedusaDesigner
import time
import matterlab_nmr as nmr
import matterlab_spectrometers as spectrometer
import uv_vis_utils as uv_vis
#spectrometers still missing


#Setup logging for Medusa liquid transfers
logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


layout = input("Design .json path\n") 
medusa = Medusa(
    graph_layout=layout,
    logger=logger     
)



"""
#ideally put into its own module, but for now just import here
# Definition of added volumes and reaction temperature by user before reaction:
"""
solvent_volume= 10 
solvent_draw_speed = solvent_volume / 2  # draw speed in mL/min
monomer_volume=4
monomer_draw_speed = monomer_volume / 2  # draw speed in mL/min
initiator_volume = 3
initiator_draw_speed = initiator_volume / 2  # draw speed in mL/min
cta_volume= 4
cta_draw_speed = cta_volume / 2  # draw speed in mL/min
polymerization_temp= 20
set_rpm = 200


Functionalization_temp = 20  # Temperature for functionalization step
Functionanilzation_volume = 2 # Volume for functionalization step
Functionalization_draw_speed = Functionanilzation_volume / 2  # draw speed in mL/min


#take the reaction vial out of the heatplate
medusa.write_serial("COM12", "2000")  # Move the reaction vial out of the heatplate

# preheat heatplate
medusa.heat_stir(vessel="Reaction_Vial", temperature= polymerization_temp, rpm= set_rpm)

# open gas valve (in default mode, gas flow will be blocked)
medusa.write_serial("COM12","GAS_ON")

# prime tubing (from vial to waste)
medusa.transfer_volumetric(source="Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Monomer_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Modification_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="Initiator_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= 1, transfer_type="liquid")
medusa.transfer_volumetric(source="CTA_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= 1, transfer_type="liquid")

# shut gas valve 
medusa.write_serial("COM12","GAS_OFF")


#lock and shim NMR
    # pump deuterated solvent to NMR
medusa.transfer_volumetric(source="Deuterated_Solvent", target="NMR", pump_id="Analytical_Pump", volume=3.5, transfer_type="liquid")
    # lock and shim NMR on deuterated solvent
        # different process, needs to be implemented still
    # pump deuterated solvent back
medusa.transfer_volumetric(source="NMR", target="Deuterated_Solvent", pump_id="Analytical_Pump", volume=3.5, transfer_type="liquid")


# fill reaction vial with things for reaction and flush it to the vial 
medusa.transfer_volumetric(source="Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= solvent_volume, transfer_type="liquid", flush=3, draw_speed=solvent_draw_speed)
medusa.transfer_volumetric(source="Monomer_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= monomer_volume, transfer_type="liquid", flush=3, draw_speed=monomer_draw_speed)
medusa.transfer_volumetric(source="Initiator_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= initiator_volume, transfer_type="liquid",flush=3, draw_speed=initiator_draw_speed)
medusa.transfer_volumetric(source="CTA_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= cta_volume, transfer_type="liquid",flush=3, draw_speed=cta_draw_speed)

# wait for heat plate to reach x degree (defined earlier)
while medusa.get_hotplate_temperature("Reaction_Vial") < polymerization_temp-2:
    time.sleep(2)


# Lower vial into heat plate
medusa.write_serial("COM12", "1000")

iteration_counter = 0
# Wait for NMR feedback regarding conversion before change to next step
while polymerization_conversion < 80:
  iteration_counter += 1
        # Pump 3 mL from reaction vial to NMR
  medusa.transfer_volumetric(source="Reaction_Vial", target="NMR", pump_id="Analytical_Pump", volume=3, transfer_type="liquid")
        # Take NMR spectrum and evaluate signal at ca. 5.5 ppm with regards to signal intensity of same signal at beginning
        # Pump 3 mL from NMR back to reaction vial and flush rest into vial with argon
  medusa.transfer_volumetric(source="NMR", target="Reaction_Vial", pump_id="Analytical_Pump", volume=3, transfer_type="liquid")   
        #wait for 5 minutes   
  time.sleep(300)
  #after 5 iterations of the previous loop, the NMR is reshimmed
  if iteration_counter % 6 == 0:
        # pump deuterated solvent to NMR
    medusa.transfer_volumetric(source="Deuterated_Solvent", target="NMR", pump_id="Analytical_Pump", volume=3, transfer_type="liquid")
        # shim NMR on deuterated solvent
            # different process, needs to be implemented still

        # pump deuterated solvent back
    medusa.transfer_volumetric(source="NMR", target="Deuterated_Solvent", pump_id="Analytical_Pump", volume=5, transfer_type="liquid")


    # Stop heatplate
medusa.heat_stir("Reaction_Vial", temperature=0)
    # Also remove vial from heatplate with linear actuator
medusa.write_serial("COM12", "2000")

    # Start peristaltic pumps   
medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW = True, transfer_rate=0.7)
medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW = False, transfer_rate=0.7)

iteration_counter = 0
while dialysis_conversion < 90:
  iteration_counter += 1
        # Pump 3 mL from reaction vial to NMR and evaluate "conversion in comparison to last NMR from polzmerization"
  medusa.transfer_volumetric(source="Reaction_Vial", target="NMR", pump_id="Analytical_Pump", volume=3, transfer_type="liquid")
        # Take NMR spectrum and evaluate signal at ca. 5.5 ppm with regards to signal intensity of same signal at beginning
        # Pump 3 mL from NMR back to reaction vial and flush rest into vial with argon
  medusa.transfer_volumetric(source="NMR", target="Reaction_Vial", pump_id="Analytical_Pump", volume=5, transfer_type="liquid")
  #wait for 5 minutes
  time.sleep(300)

  #after 6 iterations of the previous loop, the NMR is reshimmed
  if iteration_counter % 6 == 0:
        # pump deuterated solvent to NMR
    medusa.transfer_volumetric(source="Deuterated_Solvent", target="NMR", pump_id="Analytical_Pump", volume=3, transfer_type="liquid")
        # shim NMR on deuterated solvent
            # different process, needs to be implemented still

        # pump deuterated solvent back
    medusa.transfer_volumetric(source="NMR", target="Deuterated_Solvent", pump_id="Analytical_Pump", volume=5, transfer_type="liquid")

    


#when 90% conversion reached
    # pump peristaltic pump tubing empty for polymer pump in different direction and stop eluent pump
medusa.transfer_continuous(source="Reaction_Vial", target="Waste_Vessel", pump_id="Polymer_Peri_Pump", direction_CW = False, transfer_rate=0.7)
medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW = False, transfer_rate=0)
    #wait for 10 min to pump fully empty
time.sleep(600)

#turn off eluent pump
medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW = False, transfer_rate=0)

   

#add functionalization step
#degas reaction vial
medusa.write_serial("COM12","GAS_ON")
medusa.transfer_volumetric(source="Reaction_Vial", target="Waste_Vessel", pump_id="Analytical_Pump", volume= 30, transfer_type="liquid", flush=3, dispense_speed=3)
medusa.write_serial("COM12","GAS_OFF")

#first measurement of UV_VIS and use this as the baseline spectrum
uv_vis.take_spectrum(baseline = True)


#add functionalization reagent and flush into reaction vial
medusa.transfer_volumetric(source="Modification_Vessel", target="Reaction_Vial", pump_id="Functionalization_Pump", volume= Functionanilzation_volume, transfer_type="liquid", flush=3, draw_speed=Functionalization_draw_speed, dispense_speed=2)



#start flow through UV_VIS
#first add nmr solvent to the UV_VIS cell and measure background spectrum
medusa.transfer_volumetric(source="NMR_Solvent_Vessel", target="UV_VIS", pump_id="Analytical_Pump", volume= 0.7, transfer_type="liquid", flush=3, draw_speed=0.5, dispense_speed=0.5)

  #measure background spectrum

  #remove nmr solvent from UV_VIS cell
medusa.transfer_volumetric(source="UV_VIS", target="NMR_Solvent_Vessel", pump_id="Analytical_Pump", volume= 1.5, transfer_type="liquid", flush=3, draw_speed=1, dispense_speed=4)

#flow will go on until stopped by other command (use of async or threading)
medusa.transfer_volumetric(source="Reaction_Vial", target="UV_VIS", pump_id="Analytical_Pump", volume= 2, transfer_type="liquid", flush=3, draw_speed=Functionalization_draw_speed, dispense_speed=1)


#after first functionalization step, the UV_VIS cell is full
#take first UV_VIS measurement

#then add functionalization reagent








#add UV_VIS measurement and evaluation (in the beginning without addition and then continously)


#once UV_VIS measurement is done 

    #open gas valve and pump 10 mL of argon to reaction vial through the UV_VIS cell
medusa.write_serial("COM12","GAS_ON")
medusa.transfer_volumetric(source="Gas_Reservoir_Vessel", target="UV_VIS", pump_id="Analytical_Pump", volume= 10, transfer_type="gas", dispense_speed=10, flush=3)
    #close gas valve
medusa.write_serial("COM12","GAS_OFF")

#another round of dialysis (with peristaltic pumps)




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






#pump 25 mL of methanol to the precipitation module
medusa.transfer_volumetric(source="Methanol_Vessel", target="Precipitation_Vessel_Solenoid", pump_id="Precipitation_Pump", volume= 25, transfer_type="liquid", flush=3)








#pump 25 mL of methanol to the precipitation module#







#clean all the flow paths












