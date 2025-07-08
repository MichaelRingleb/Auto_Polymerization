"""
medusa_designer_setup.py

This module provides utilities for designing and editing experimental setups for volumetric transfers
using the Medusa Designer GUI. It allows users to create new designs or open and modify existing ones
through an interactive web interface.

Functions:
    - make_new_design(): Launches the Medusa Designer GUI for creating a new experimental setup.
    - add_to_existing_design(): Prompts the user for a JSON file path and opens the design in the Medusa Designer GUI for editing.
    - json_to_dictionary(json_path): Utility function to load a JSON file as a Python dictionary.

Typical usage:
    Run this script directly to open an existing design for editing:
        $ python medusa_designer_setup.py

    Or import and use the functions in other scripts for workflow automation.

Requirements:
    - medusa (medusa-sdl) package installed and importable in your environment.
    - Python 3.7 or higher.

Author: Michael Ringleb
"""


from pathlib import Path
from medusa import Medusa, MedusaDesigner
import logging
import json

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def make_new_design():
    designer = MedusaDesigner()
    designer.new_design()
    exit()
    input()
    return designer


def add_to_existing_design():
    """
    Opens an existing Medusa design in the GUI for editing.
    Args:
        json_path (str): Path to the JSON file containing the design.
    """
    json_path = input("Please enter the path to the current json file of your design:")
    with open(json_path, "r") as f:
        design_dict = json.load(f)
    designer = MedusaDesigner(template=design_dict)
    designer.new_design()
    exit()
    input()
    return designer



if __name__ == "__main__":
    # Example usage: open an existing design
    #add_to_existing_design()
    make_new_design()

    