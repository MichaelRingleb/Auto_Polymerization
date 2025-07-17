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
    "uv_vis" : 2 
}

dispense_speeds = {
    "solvent": 8,
    "monomer": 8,
    "initiator": 8,
    "cta": 8,
    "modification": 3,
    "nmr" : 3,
    "uv_vis" : 2
}


# Default volumes for each component (mL)
default_volumes = {
    "solvent": 10,
    "monomer": 4,
    "initiator": 3,
    "cta": 4,
    "modification" : 2,
    "nmr" : 3,
    "uv_vis" : 2
}

# Reaction temperature for polymerization (C)
polymerization_temp = 20

# Stirring speed (rpm)
set_rpm = 600

# Degassing time (seconds)
degas_time = 1200

# Modification step parameters
functionalization_temp = 20  # Temperature for functionalization step


# Add more user-editable parameters as needed below 