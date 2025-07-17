"""
_0_preparation.py

Preparation module for the Auto_Polymerization workflow.
Encapsulates all steps required to prepare the system before polymerization, including NMR shimming, vial handling, heatplate preheating, gas valve control, and tubing priming.

All user-editable settings (draw_speeds, dispense_speeds, volumes, temperatures, etc.) should be set in users/config/platform_config.py and supplied as arguments from the controller.

Supported keys for draw_speeds and dispense_speeds include: 'solvent', 'monomer', 'initiator', 'cta', 'modification', 'nmr', 'uv_vis'.

All functions are designed to be called from a workflow controller script.
"""
# Example usage:
# from users.config import platform_config as config
# draw_speeds = config.draw_speeds
# dispense_speeds = config.dispense_speeds
# polymerization_temp = config.polymerization_temp
# set_rpm = config.set_rpm

# All transfer calls use .get() for draw_speeds and dispense_speeds, so new keys are supported automatically.
# If you add new components to the config, ensure to use the same keys in your workflow logic.


def shim_nmr_sample(medusa, volume=3, pump_id="Analytical_Pump", source="Deuterated_Solvent", target="NMR", shim_level=2, shim_repeats=2, draw_speed=6, dispense_speed=6):
    """
    Transfer deuterated solvent to NMR, perform shimming, and return solvent to the original vessel.
    Args:
        medusa: Medusa instance for liquid handling
        volume: Volume to transfer (default 3)
        pump_id: Pump to use (default 'Analytical_Pump')
        source: Source vessel (default 'Deuterated_Solvent')
        target: Target vessel (default 'NMR')
        shim_level: Shimming level (default 2)
        shim_repeats: Number of shimming repetitions (default 2)
        draw_speed: Syringe draw speed (from config or controller)
        dispense_speed: Syringe dispense speed (from config or controller)
    """
    import src.NMR.nmr_utils as nmr
    medusa.logger.info("Transferring deuterated solvent to NMR for shimming...")
    medusa.transfer_volumetric(source=source, target=target, pump_id=pump_id, volume=volume, transfer_type="liquid", draw_speed=draw_speed, dispense_speed=dispense_speed)
    for _ in range(shim_repeats):
        nmr.run_shimming(shim_level)
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


def prime_tubing(medusa, volume=3, draw_speeds=None, dispense_speeds=None):
    """
    Prime tubing from each vessel to waste using the appropriate pumps.
    Args:
        medusa: Medusa instance
        volume: Volume to prime from each vessel (default 3)
        draw_speeds: dict mapping component names to draw speeds (must be supplied by caller)
        dispense_speeds: dict mapping component names to dispense speeds (must be supplied by caller)
    Notes:
        Uses .get() for each component, so missing keys will use a default value of 3.
        Adds flush=1 to each transfer for effective priming.
    """
    if draw_speeds is None:
        draw_speeds = {}
    if dispense_speeds is None:
        dispense_speeds = {}
    medusa.logger.info("Priming tubing from solvent, monomer, modification, initiator, and CTA vessels to waste...")
    medusa.transfer_volumetric(source="Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("solvent", 3), dispense_speed=dispense_speeds.get("solvent", 3), flush=1)
    medusa.transfer_volumetric(source="Monomer_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("monomer", 3), dispense_speed=dispense_speeds.get("monomer", 3), flush=1)
    medusa.transfer_volumetric(source="Modification_Vessel", target="Waste_Vessel", pump_id="Solvent_Monomer_Modification_Pump", volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("modification", 3), dispense_speed=dispense_speeds.get("modification", 3), flush=1)
    medusa.transfer_volumetric(source="Initiator_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("initiator", 3), dispense_speed=dispense_speeds.get("initiator", 3), flush=1)
    medusa.transfer_volumetric(source="CTA_Vessel", target="Waste_Vessel", pump_id="Initiator_CTA_Pump", volume=volume, transfer_type="liquid", draw_speed=draw_speeds.get("cta", 3), dispense_speed=dispense_speeds.get("cta", 3), flush=1)


def close_gas_valve(medusa):
    """
    Close the gas valve.
    Args:
        medusa: Medusa instance
    """
    medusa.logger.info("Closing gas valve...")
    medusa.write_serial("GAS_VALVE", "GAS_OFF")


def run_preparation_workflow(
    medusa,
    polymerization_temp,
    set_rpm,
    shim_kwargs=None,
    prime_volume=3,
    run_minimal_test=False,
    draw_speeds=None,
    dispense_speeds=None
):
    """
    Execute the full preparation workflow in parallel:
    - NMR shimming (solvent transfer, shimming, return)
    - All other steps (vial/heatplate, gas valve, priming)
    Both must finish before returning.

    Optionally runs the minimal workflow test at the start if run_minimal_test is True.

    Args:
        medusa: Medusa instance
        polymerization_temp: Target temperature for polymerization
        set_rpm: Stirring speed (rpm)
        shim_kwargs: Optional dict of keyword arguments for shim_nmr_sample
        prime_volume: Volume to use for priming (default 3)
        run_minimal_test: If True, runs the minimal workflow test before preparation
        draw_speeds: dict mapping component names to draw speeds (must be supplied by caller)
        dispense_speeds: dict mapping component names to dispense speeds (must be supplied by caller)
    Notes:
        This function orchestrates the preparation phase of the polymerization reaction.
        It includes shimming the NMR spectrometer with deuterated solvent, removing the reaction vial from the heatplate, preheating the heatplate,
        and priming the tubings from the reaction component stock vials to the pumps.
        The minimal workflow test gives the user the chance to check the hardware before the actual workflow starts.
        All steps are executed in parallel using threading and both must finish before returning.
    """
    import threading
    if run_minimal_test:
        from Auto_Polymerization.tests.test_minimal_workflow import run_minimal_workflow_test
        run_minimal_workflow_test(medusa)

    if shim_kwargs is None:
        shim_kwargs = {}
    if draw_speeds is None:
        draw_speeds = {}
    if dispense_speeds is None:
        dispense_speeds = {}

    # Define the two subworkflows as functions
    def nmr_shim_workflow():
        # Use draw_speeds and dispense_speeds for NMR shimming if provided
        shim_nmr_sample(
            medusa,
            draw_speed=draw_speeds.get("nmr", 6),
            dispense_speed=dispense_speeds.get("nmr", 6),
            **shim_kwargs
        )

    def other_prep_workflow():
        prepare_reaction_vial_and_heatplate(medusa, polymerization_temp, set_rpm)
        open_gas_valve(medusa)
        prime_tubing(medusa, volume=prime_volume, draw_speeds=draw_speeds, dispense_speeds=dispense_speeds)
        close_gas_valve(medusa)

    # Create threads for parallel execution
    t1 = threading.Thread(target=nmr_shim_workflow)
    t2 = threading.Thread(target=other_prep_workflow)

    # Start both threads
    t1.start()
    t2.start()

    # Wait for both to finish
    t1.join()
    t2.join() 