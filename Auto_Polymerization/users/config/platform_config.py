"""
platform_config.py

User-editable platform configuration for Auto_Polymerization.

This file defines all workflow and transfer parameters for the platform, including:
- Priming, NMR shimming, NMR sampling, and UV-VIS transfer parameters
- Draw/dispense speeds, volumes, temperatures, timings, and RPMs for all workflow steps

All parameters defined here are passed unchanged to the error-safe transfer logic (serial_communication_error_safe_transfer_volumetric),
which is a direct, parameter-preserving wrapper for medusa.transfer_volumetric. Only parameter values should be changed by users;
parameter names and structure must be preserved for correct operation.

If you change tubing lengths, vessel sizes, or hardware, update the relevant volume values here.
Do not rename or remove keys unless you are also updating the workflow code.
"""



#Parameters for the preparation workflow substep, change, if you have longer lines, which are not sufficiently primed with the current volumes 
prime_transfer_params = { 
    "prime_volume": 1,
    "draw_speed": 0.07,
    "dispense_speed": 0.1,
    "flush": 1,
    "flush_volume": 5,
    "flush_speed": 0.2,
    "pre_rinse": 2,
    "pre_rinse_volume": 0.5,
    "pre_rinse_speed": 0.1,
    "post_rinse": 1,
    "post_rinse_volume": 2.5,
    "post_rinse_speed": 0.1,
}

#Parameters for the polymerization workflow substep, change, if you want to use different volumes for the reaction components
polymerization_params = { 
    "solvent_volume": 10,
    "solvent_draw_speed": 0.08,
    "solvent_dispense_speed": 0.13,
    "monomer_volume": 4,
    "monomer_draw_speed": 0.08,
    "monomer_dispense_speed": 0.13,
    "cta_volume": 4,
    "cta_draw_speed": 0.08,
    "cta_dispense_speed": 0.13,
    "initiator_volume": 3,
    "initiator_draw_speed": 0.08,
    "initiator_dispense_speed": 0.13,
    "flush": 2,
    "flush_volume": 5,
    "flush_speed": 0.3,
    "pre_rinse": 1,
    "pre_rinse_volume": 0.5,
    "pre_rinse_speed": 0.1,
    "post_rinse": 1,
    "post_rinse_volume": 2.5,
    "last_post_rinse_volume": 6,
    "post_rinse_speed": 0.133,
    "post_rinse_vessel": "Purge_Solvent_Vessel_1",
}

# Timing and workflow-specific parameters (seconds, iterations, etc.)
timings = {
    "deoxygenation_time": 1200, #20 min
    "functionalization_interval_sec": 180,  # 3 minutes
    "functionalization_max_iterations": 200,
    "precipitation_wait_sec": 600,
    
}

# Temperatures for various steps (C)
temperatures = {
    "polymerization_temp": 75,
    "functionalization_temp": 30,
    "cleaning_dry_temp": 80,
}

# RPM settings for various steps
target_rpm = {
    "polymerization_rpm": 600,
    "cleaning_rpm": 300,
}


#Parameters for the analytical transfers (NMR shimming, NMR sampling, UV-VIS)
#change if you changed the length of the tubing or the volume of the NMR cell 
nmr_transfer_params = {
    # Parameters for NMR shimming transfer (deuterated solvent)
    "shimming": {
        "volume": 2.1,
        "draw_speed": 0.07,
        "dispense_speed": 0.07,
        "post_rinse": 1,
        "post_rinse_volume": 1.5,
        "post_rinse_speed": 0.1,
        "post_rinse_vessel": "Purge_Solvent_Vessel_2",
        "transfer_type": "liquid"
    },
    # Parameters for NMR sampling transfer (reaction/sample)
    "sampling": {
        "volume": 2.1,
        "draw_speed": 0.05,
        "dispense_speed": 0.05,
        "post_rinse": 1,
        "post_rinse_volume": 2.5,
        "post_rinse_speed": 0.1,
        "post_rinse_vessel": "Purge_Solvent_Vessel_2",
        "transfer_type": "liquid"
    }
}
#change if you changed the length of the tubing to the UV-VIS cell
uv_vis_transfer_params = {
    "volume": 1.5,
    "draw_speed": 0.03,
    "dispense_speed": 0.016,
    "post_rinse": 1,
    "post_rinse_volume": 1.5,
    "post_rinse_speed": 0.1,
    "post_rinse_vessel": "Purge_Solvent_Vessel_2",
    "transfer_type": "liquid"
}



draw_speeds = {
    "solvent": 0.08,
    "monomer": 0.08,
    "initiator": 0.08,
    "cta": 0.08,
    "modification": 0.08,
    "nmr": 0.05,
    "uv_vis": 0.03,
    "functionalization": 0.03,
    "precipitation": 0.16,
    "cleaning": 0.16,
}

dispense_speeds = {
    "solvent": 0.13,
    "monomer": 0.13,
    "initiator": 0.13,
    "cta": 0.13,
    "modification": 0.05,
    "nmr": 0.05,
    "uv_vis": 0.016,
    "functionalization": 0.032,
    "precipitation": 0.33,
    "cleaning": 0.05,
}

# Default volumes for different transfers / components
default_volumes = {
    "prime" : 2,
    "solvent": 10,
    "monomer": 4,
    "initiator": 3,
    "cta": 4,
    "modification": 2,
    "nmr": 2.1,
    "uv_vis": 1.5,
    "flush": 5,
    "functionalization": 2,
    "precipitation_methanol": 25,
    "precipitation_argon": 100,
    "cleaning_purge_solvent": 30,
    "cleaning_dry_argon": 200
    
}










# Add more user-editable parameters as needed below 