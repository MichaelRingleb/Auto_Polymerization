#Module to design own experimental setup (for volumetric transfers) with Medusa designer
from pathlib import Path
from medusa import Medusa, MedusaDesigner


#opens the webinterface for the designer and saves design to json (in Downloads folder)
designer = MedusaDesigner()
designer.new_design()
exit()
input()

"""
#Show design  → implement later on (for now: screenshot in the Fluid transfers scheme folder)
design_path = input("Path to your design file (e.g. 'path/to/your_design.json'): ")
designer = Medusa(design_path)
Medusa.view_layout(designer)
"""
