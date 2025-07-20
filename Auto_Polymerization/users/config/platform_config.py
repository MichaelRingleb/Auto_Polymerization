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


# Experiment ID and base path for data storage
experiment_id= "MRG_061_I"
data_base_path = "users/data"
nmr_data_base_path = "users/data/NMR_data"  # Specific NMR data directory


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


# -------------------------------------------------------------------
# Polymerization Monitoring Parameters
# Used for both polymerization and dialysis shimming intervals, etc.
# -------------------------------------------------------------------
# Polymerization monitoring parameters
polymerization_monitoring_params = {
    "nmr_monomer_region": (5.0, 6.0),  # ppm range for monomer peaks
    "nmr_standard_region": (6.5, 7.5),  # ppm range for internal standard peaks
    "nmr_noise_region": (9.0, 10.0),  # ppm range for baseline noise calculation
    "nmr_scans": 32,  # Number of NMR scans per measurement
    "nmr_spectrum_center": 5,  # ppm center of NMR spectrum
    "nmr_spectrum_width": 12,  # ppm width of NMR spectrum
    "measurement_interval_minutes": 10,  # Time between measurements
    "shimming_interval": 4,  # Reshim every N measurements
    "conversion_threshold": 80,  # Stop at this conversion %
    "max_monitoring_hours": 20,  # Maximum monitoring time, after this time the workflow will stop and continue with the next step
}



# Temperatures for various steps (C)
temperatures = {
    "polymerization_temp": 75,
    "functionalization_temp": 30,
    "cleaning_dry_temp": 80,
}

# -------------------------------------------------------------------
# Dialysis Workflow Parameters
# Only dialysis-specific booleans and references to shared config values.
# -------------------------------------------------------------------
dialysis_params = {
    "noise_comparison_based": True,      # If True, stop dialysis when monomer peak < 3x noise (NMR-based)
    "time_based": True,            # If True, stop dialysis after a set duration (see below)
    "dialysis_duration_mins": 180, # Duration (in minutes) for time-based stopping
    "dialysis_measurement_interval_minutes": None,  # If set, overrides monitoring interval for dialysis. If None, uses polymerization_monitoring_params["measurement_interval_minutes"].
    # The following parameters are referenced from other config dicts:
    # "sample_volume_ml": nmr_transfer_params['sample_volume_ml']
    # "reshim_interval": polymerization_monitoring_params['shimming_interval']
    # NMR regions for dialysis are the same as for monitoring.
}

# RPM settings for various steps
target_rpm = {
    "polymerization_rpm": 600,
    "cleaning_rpm": 300,
}
# -------------------------------------------------------------------
# NMR Transfer Parameters
# Used for all NMR sample transfers (monitoring, t0, dialysis, etc.)
# -------------------------------------------------------------------
# Parameters for the analytical transfers (NMR shimming, NMR sampling, UV-VIS)
#change if you changed the length of the tubing or the volume of the NMR cell 
nmr_transfer_params = {
    # Parameters for NMR shimming transfer (deuterated solvent)
    "shimming": {
        "volume": 2.1,
        "draw_speed": 0.07,
        "dispense_speed": 0.07,
        "flush": 1,
        "flush_volume": 5,
        "flush_speed": 0.15,
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
        "dispense_speed": 0.05,"flush": 1,
        "flush_volume": 5,
        "flush_speed": 0.15,
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