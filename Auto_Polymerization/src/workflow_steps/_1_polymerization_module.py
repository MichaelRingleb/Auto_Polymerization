#open gas valve again (for flush steps)
medusa.write_serial("Gas_Valve","GAS_ON")
#fill reaction vial with things for reaction and flush it to the vial 
medusa.transfer_volumetric(source="Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= solvent_volume, transfer_type="liquid", flush=1, draw_speed=solvent_draw_speed)
medusa.transfer_volumetric(source="Monomer_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume= monomer_volume, transfer_type="liquid", flush=1, draw_speed=monomer_draw_speed)
medusa.transfer_volumetric(source="Initiator_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= initiator_volume, transfer_type="liquid",flush=2, draw_speed=initiator_draw_speed)
medusa.transfer_volumetric(source="CTA_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume= cta_volume, transfer_type="liquid",flush=2, draw_speed=cta_draw_speed)

#degass reaction mixture for 20 min
time.sleep(degas_time)


#close gas valve again
medusa.write_serial("Gas_Valve","GAS_OFF")


# wait for heat plate to reach x degree (defined earlier)
while medusa.get_hotplate_temperature("Reaction_Vial") < polymerization_temp-2:
    time.sleep(2)
    medusa.get_hotplate_rpm("Reaction_Vial")


# THEN; Lower vial into heat plate
medusa.write_serial("Linear_Actuator", "1000")