from src.liquid_transfers.liquid_transfers_utils import serial_communication_error_safe_transfer_volumetric
import time


def run_polymerization_workflow(medusa, params):
    #open gas valve again (for flush steps)
    medusa.write_serial("Gas_Valve","GAS_ON")
    #fill reaction vial with things for reaction and flush it to the vial 
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "Solvent_Vessel", "target": "Reaction_Vial", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": "liquid",
        "flush": 1, "draw_speed": params["solvent_draw_speed"],
        "volume": params["solvent_volume"], 
    })
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "Monomer_Vessel", "target": "Reaction_Vial", "pump_id": "Solvent_Monomer_Modification_Pump",
        "transfer_type": "liquid", 
        "flush": 2, "draw_speed": params["monomer_draw_speed"]
        "volume": params["monomer_volume"], 
    })
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "CTA_Vessel", "target": "Reaction_Vial", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": "liquid", 
        "flush": 2, "draw_speed": params["cta_draw_speed"]
        "volume": params["cta_volume"],
    })
    serial_communication_error_safe_transfer_volumetric(medusa, {
        "source": "Initiator_Vessel", "target": "Reaction_Vial", "pump_id": "Initiator_CTA_Pump",
        "transfer_type": "liquid", "flush": 2, "draw_speed": params["initiator_draw_speed"]
        "volume": params["initiator_volume"],
    })
    

    #degass reaction mixture for 20 min
    time.sleep(params["degas_time"])

    #close gas valve again
    medusa.write_serial("Gas_Valve","GAS_OFF")

    # wait for heat plate to reach x degree (defined earlier)
    while medusa.get_hotplate_temperature("Reaction_Vial") < params["polymerization_temp"]-2:
        time.sleep(2)
        medusa.get_hotplate_rpm("Reaction_Vial")

    # THEN; Lower vial into heat plate
    medusa.write_serial("Linear_Actuator", "1000")