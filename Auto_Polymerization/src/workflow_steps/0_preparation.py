"""
0_preparation.py

Preparation module for the Auto_Polymerization workflow.
Encapsulates all steps required to prepare the system before polymerization, including NMR shimming, vial handling, heatplate preheating, gas valve control, and tubing priming.

All functions are designed to be called from a workflow controller script.
"""

import threading

def initial_shim_nmr_sample(medusa, nmr, volume=3, pump_id="Analytical_Pump", source="Deuterated_Solvent", target="NMR", shim_level=2, shim_repeats=2, draw_speed=6, dispense_speed=6):
    """
    Pump deuterated solvent to NMR, run shimming, and transfer back to solvent vessel.
    Args:
        medusa: Medusa instance for liquid handling
        nmr: NMR instrument instance
        volume: Volume to transfer (default 3)
        pump_id: Pump to use (default 'Analytical_Pump')
        source: Source vessel (default 'Deuterated_Solvent')
        target: Target vessel (default 'NMR')
        shim_level: Shimming level (default 2)
        shim_repeats: Number of shimming repetitions (default 2)
        draw_speed: Syringe draw speed
        dispense_speed: Syringe dispense speed
    """
    medusa.logger.info("Transferring deuterated solvent to NMR for shimming...")
    medusa.transfer_volumetric(source=source, target=target, pump_id=pump_id, volume=volume, transfer_type="liquid", draw_speed=draw_speed, dispense_speed=dispense_speed)
    for _ in range(shim_repeats):
        nmr.shim(shim_level)
        medusa.logger.info(f"NMR shimming (level {shim_level}) complete.")
    medusa.logger.info("Transferring solvent back to deuterated solvent vessel...")
    medusa.transfer_volumetric(source=target, target=source, pump_id=pump_id, volume=volume, transfer_type="liquid", draw_speed=draw_speed, dispense_speed=dispense_speed)


def prepare_reaction_vial_and_heatplate(medusa, polymerization_temp, set_rpm):
    """
    Move the reaction vial out of the heatplate and preheat the heatplate.
    Args:
        medusa: Medusa instance
        polymerization_temp: Target temperature for polymerization
        set_rpm: Stirring speed (rpm)
    """
    medusa.logger.info("Moving reaction vial out of heatplate...")
    medusa.write_serial("Linear_Actuator", "2000")
    medusa.logger.info(f"Preheating heatplate to {polymerization_temp}°C and setting RPM to {set_rpm}...")
    medusa.heat_stir(vessel="Reaction_Vial", temperature=polymerization_temp, rpm=set_rpm)


def open_gas_valve(medusa):
    """
    Open the gas valve (default mode: gas flow blocked).
    Args:
        medusa: Medusa instance
    """
    medusa.logger.info("Opening gas valve...")
    medusa.write_serial("GAS_VALVE", "GAS_ON")


def prime_tubing(medusa, volume=1):
    """
    Prime tubing from each vessel to waste using the appropriate pumps.
    Args:
        medusa: Medusa instance
        volume: Volume to prime from each vessel (default 3)
    """
    medusa.logger.info("Priming tubing from solvent, monomer, modification, initiator, and CTA vessels to waste...")
    medusa.transfer_volumetric(source="Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume=volume, transfer_type="liquid")
    medusa.transfer_volumetric(source="Monomer_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume=volume, transfer_type="liquid")
    medusa.transfer_volumetric(source="Modification_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume=volume, transfer_type="liquid")
    medusa.transfer_volumetric(source="Initiator_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume=volume, transfer_type="liquid")
    medusa.transfer_volumetric(source="CTA_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume=volume, transfer_type="liquid")


def close_gas_valve(medusa):
    """
    Close the gas valve.
    Args:
        medusa: Medusa instance
    """
    medusa.logger.info("Closing gas valve...")
    medusa.write_serial("GAS_VALVE", "GAS_OFF")


def run_preparation_workflow(medusa, nmr, polymerization_temp, set_rpm, shim_kwargs=None, prime_volume=3):
    """
    Execute the full preparation workflow in parallel:
    - NMR shimming (solvent transfer, shimming, return)
    - All other steps (vial/heatplate, gas valve, priming)
    Both must finish before returning.
    """
    if shim_kwargs is None:
        shim_kwargs = {}

    # Define the two subworkflows as functions
    def nmr_shim_workflow():
        initial_shim_nmr_sample(medusa, nmr, **shim_kwargs)

    def other_prep_workflow():
        prepare_reaction_vial_and_heatplate(medusa, polymerization_temp, set_rpm)
        open_gas_valve(medusa)
        prime_tubing(medusa, volume=prime_volume)
        close_gas_valve(medusa)

    # Create threads
    t1 = threading.Thread(target=nmr_shim_workflow)
    t2 = threading.Thread(target=other_prep_workflow)

    # Start both
    t1.start()
    t2.start()

    # Wait for both to finish
    t1.join()
    t2.join() 