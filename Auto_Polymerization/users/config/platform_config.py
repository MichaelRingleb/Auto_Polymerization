# User-editable platform configuration for Auto_Polymerization
# Edit this file to change platform-wide settings and workflow parameters.

# Draw speeds for each component (mL/min)
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
    "solvent": 10,
    "monomer": 4,
    "initiator": 3,
    "cta": 4,
    "modification": 2,
    "nmr": 2.1,
    "uv_vis": 1.5,
    "functionalization": 2,
    "precipitation_methanol": 25,
    "precipitation_argon": 100,
    "cleaning_purge_solvent": 30,
    "cleaning_dry_argon": 200,
    "prime" : 2
}

# Timing and workflow-specific parameters (seconds, iterations, etc.)
timings = {
    "degas_time": 1200,
    "functionalization_interval_sec": 180,  # 3 minutes
    "functionalization_max_iterations": 200,
    "precipitation_wait_sec": 600,
    "cleaning_dry_temp": 80,
}

# Temperatures for various steps (C)
temperatures = {
    "polymerization": 75,
    "functionalization": 20,
    "cleaning_dry": 70,
}

# RPM settings for various steps
target_rpm = {
    "polymerization": 600,
    "cleaning": 300,
}

# Add more user-editable parameters as needed below 