#Module to design own experimental setup (for volumetric transfers) with Medusa designer
from pathlib import Path
from medusa import Medusa, MedusaDesigner
import logging

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())



#opens the webinterface for the designer and saves design to json (in Downloads folder)
designer = MedusaDesigner()
designer.new_design()
exit()
input()

"""
#Show design  → implement later on (for now: screenshot in the Fluid transfers scheme folder)
layout = input("Design path:")
medusa = Medusa(
    graph_layout=layout,
    logger=logger     
)
medusa.view_layout()  # Opens the design in the Medusa viewer)
"""