# User-editable platform configuration for Auto_Polymerization
# Edit this file to change platform-wide settings and workflow parameters.

# Draw speeds for each component (mL/min)
draw_speeds = {
    "solvent": 5,
    "monomer": 5,
    "initiator": 5,
    "cta": 5,
    "modification": 5,
    "nmr": 3,
    "uv_vis": 2,
    "functionalization": 2,
    "precipitation": 10,
    "cleaning": 10,
}

dispense_speeds = {
    "solvent": 8,
    "monomer": 8,
    "initiator": 8,
    "cta": 8,
    "modification": 3,
    "nmr": 3,
    "uv_vis": 1,
    "functionalization": 2,
    "precipitation": 20,
    "cleaning": 3,
}

# Default volumes for different transfers / components
default_volumes = {
    "solvent": 10,
    "monomer": 4,
    "initiator": 3,
    "cta": 4,
    "modification": 2,
    "nmr": 3,
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