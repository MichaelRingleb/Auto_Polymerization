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

# -------------------------------------------------------------------
# GENERAL EXPERIMENT METADATA & PATHS
# -------------------------------------------------------------------
experiment_id = "MRG_061_I"  # Unique experiment identifier
data_base_path = "users/data"  # Base directory for all experiment data
nmr_data_base_path = "users/data/NMR_data"  # Directory for NMR data (subfolder of data_base_path)
uv_vis_data_base_path = "users/data/UV_VIS_data"  # Directory for UV-VIS data (subfolder of data_base_path)


# -------------------------------------------------------------------
# TIMINGS FOR WORKFLOW STEPS (seconds unless otherwise noted)
# -------------------------------------------------------------------
timings = {
    "deoxygenation_time": 1200,                # s, time for deoxygenation (20 min) before start of polymerization
    "functionalization_interval_sec": 180,     # s, interval between functionalization measurements (3 min)
    "functionalization_max_iterations": 200,   # max iterations for functionalization (10 hours)
    "precipitation_wait_sec": 600,             # s, wait time for precipitation (10 min)
}

# -------------------------------------------------------------------
# TEMPERATURES FOR VARIOUS STEPS (°C)
# -------------------------------------------------------------------
temperatures = {
    "polymerization_temp": 75,         # °C, polymerization
    "functionalization_temp": 30,      # °C, modification/functionalization
    "cleaning_dry_temp": 80,           # °C, cleaning
}

# -------------------------------------------------------------------
# RPM SETTINGS FOR VARIOUS STEPS
# -------------------------------------------------------------------
target_rpm = {
    "polymerization_rpm": 600,   # rpm, polymerization
    "cleaning_rpm": 300,         # rpm, cleaning
}

# -------------------------------------------------------------------
# PREPARATION WORKFLOW PARAMETERS
# -------------------------------------------------------------------
# Priming and cleaning parameters for all lines and pumps
prime_transfer_params = {
    "prime_volume": 1,           # mL, volume for priming
    "draw_speed": 0.07,          # mL/s, speed for drawing liquid
    "dispense_speed": 0.1,       # mL/s, speed for dispensing liquid
    "flush": 1,                  # times, number of flushes
    "flush_volume": 5,           # mL, volume per flush
    "flush_speed": 0.2,          # mL/s, speed for flushing
    "pre_rinse": 2,              # times, number of pre-rinses
    "pre_rinse_volume": 0.5,     # mL, volume per pre-rinse
    "pre_rinse_speed": 0.1,      # mL/s, speed for pre-rinse
    "post_rinse": 1,             # times, number of post-rinses
    "post_rinse_volume": 2.5,    # mL, volume per post-rinse
    "post_rinse_speed": 0.1,     # mL/s, speed for post-rinse
}

# -------------------------------------------------------------------
# POLYMERIZATION WORKFLOW PARAMETERS
# -------------------------------------------------------------------
# Volumes and speeds for each reagent/component
polymerization_params = {
    "solvent_volume": 10,            # mL
    "solvent_draw_speed": 0.08,      # mL/s
    "solvent_dispense_speed": 0.13,  # mL/s
    "monomer_volume": 4,             # mL
    "monomer_draw_speed": 0.08,      # mL/s
    "monomer_dispense_speed": 0.13,  # mL/s
    "cta_volume": 4,                 # mL
    "cta_draw_speed": 0.08,          # mL/s
    "cta_dispense_speed": 0.13,      # mL/s
    "initiator_volume": 3,           # mL
    "initiator_draw_speed": 0.08,    # mL/s
    "initiator_dispense_speed": 0.13,# mL/s
    "flush": 2,                      # times
    "flush_volume": 5,               # mL
    "flush_speed": 0.3,              # mL/s
    "pre_rinse": 1,                  # times
    "pre_rinse_volume": 0.5,         # mL
    "pre_rinse_speed": 0.1,          # mL/s
    "post_rinse": 1,                 # times
    "post_rinse_volume": 2.5,        # mL
    "last_post_rinse_volume": 6,     # mL, final rinse
    "post_rinse_speed": 0.133,       # mL/s
    "post_rinse_vessel": "Purge_Solvent_Vessel_1", # Vessel for post-rinse
}


# -------------------------------------------------------------------
# POLYMERIZATION MONITORING & DIALYSIS MONITORING PARAMETERS
# -------------------------------------------------------------------
# Used for both polymerization and dialysis shimming intervals, etc.
polymerization_monitoring_params = {
    "nmr_monomer_region": (5.0, 6.0),      # ppm, monomer peak region
    "nmr_standard_region": (6.5, 7.5),     # ppm, internal standard region
    "nmr_noise_region": (9.0, 10.0),       # ppm, baseline noise region
    "nmr_scans": 32,                       # scans per measurement
    "nmr_spectrum_center": 5,              # ppm, spectrum center
    "nmr_spectrum_width": 12,              # ppm, spectrum width
    "measurement_interval_minutes": 10,     # min, time between measurements
    "shimming_interval": 4,                # reshim every N measurements
    "conversion_threshold": 80,            # %, stop at this conversion
    "max_monitoring_hours": 20,            # h, max monitoring time
}


# -------------------------------------------------------------------
# DIALYSIS WORKFLOW PARAMETERS
# -------------------------------------------------------------------
dialysis_params = {
    "noise_comparison_based": True,      # If True, stop dialysis when monomer peak < 3x noise (NMR-based)
    "time_based": True,                  # If True, stop dialysis after a set duration (see below)
    "dialysis_duration_mins": 300,       # min, duration for time-based stopping
    "dialysis_measurement_interval_minutes": None,  # min, overrides monitoring interval if set
    # The following parameters are referenced from other config dicts:
    # "sample_volume_ml": nmr_transfer_params['sample_volume_ml']
    # "reshim_interval": polymerization_monitoring_params['shimming_interval']
    # NMR regions for dialysis are the same as for monitoring.
}


# -------------------------------------------------------------------
# Modification WORKFLOW PARAMETERS
# -------------------------------------------------------------------
modification_params = {
    "modification_volume": 2,            # mL, volume of modification reagent
    "modification_draw_speed": 0.08,     # mL/s, speed for drawing modification reagent
    "modification_dispense_speed": 0.13, # mL/s, speed for dispensing modification reagent
    "modification_flush": 1,             # times, number of flushes
    "modification_flush_volume": 5,      # mL, volume per flush
    "modification_flush_speed": 0.15,    # mL/s, speed for flushing
    "pre_rinse": 1,                  # times
    "pre_rinse_volume": 0.7,         # mL
    "pre_rinse_speed": 0.1,          # mL/s
    "post_rinse": 1,                 # times
    "post_rinse_volume": 2.5,        # mL
    "post_rinse_speed": 0.133,       # mL/s
    "post_rinse_vessel": "Purge_Solvent_Vessel_1", # Vessel for post-rinse
    "deoxygenation_time_sec": 600,       # s, time for argon deoxygenation (10 min)
    "monitoring_interval_minutes": 3,    # min, interval between UV-VIS measurements
    "max_monitoring_iterations": 200,    # max iterations for monitoring (10 hours)
    "post_modification_dialysis_hours": 5, # h, duration for post-modification dialysis
    "uv_vis_stability_tolerance_percent": 5.0,  # %, tolerance for absorbance stability check
    "uv_vis_stability_measurements": 10, # number of recent measurements to compare for stability
}


# -------------------------------------------------------------------
# NMR TRANSFER PARAMETERS (used for all NMR sample transfers)
# -------------------------------------------------------------------
# Change if you changed the length of the tubing or the volume of the NMR cell
nmr_transfer_params = {
    # Parameters for NMR shimming transfer (deuterated solvent)
    "shimming": {
        "volume": 2.1,                # mL
        "draw_speed": 0.07,           # mL/s
        "dispense_speed": 0.07,       # mL/s
        "flush": 1,                   # times
        "flush_volume": 5,            # mL
        "flush_speed": 0.15,          # mL/s
        "post_rinse": 1,              # times
        "post_rinse_volume": 1.5,     # mL
        "post_rinse_speed": 0.1,      # mL/s
        "post_rinse_vessel": "Purge_Solvent_Vessel_2",
        "transfer_type": "liquid"
    },
    # Parameters for NMR sampling transfer (reaction/sample)
    "sampling": {
        "volume": 2.1,                # mL
        "draw_speed": 0.05,           # mL/s
        "dispense_speed": 0.05,       # mL/s
        "flush": 1,                   # times
        "flush_volume": 5,            # mL
        "flush_speed": 0.15,          # mL/s
        "post_rinse": 1,              # times
        "post_rinse_volume": 2.5,     # mL
        "post_rinse_speed": 0.1,      # mL/s
        "post_rinse_vessel": "Purge_Solvent_Vessel_2",
        "transfer_type": "liquid"
    }
}

# -------------------------------------------------------------------
# UV-VIS TRANSFER PARAMETERS (change if you changed tubing length to UV-VIS cell)
# -------------------------------------------------------------------
uv_vis_transfer_params = {
    "volume": 1.5,                # mL
    "reference_volume": 0.7,       # mL
    "draw_speed": 0.03,           # mL/s
    "dispense_speed": 0.016,      # mL/s
    "post_rinse": 1,              # times
    "post_rinse_volume": 1.5,     # mL
    "post_rinse_speed": 0.1,      # mL/s
    "post_rinse_vessel": "Purge_Solvent_Vessel_2",
    "transfer_type": "liquid"
}



# -------------------------------------------------------------------
# Add more user-editable parameters as needed below
# ------------------------------------------------------------------- 