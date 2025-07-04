#Module to design own experimental setup (for volumetric transfers) with Medusa designer
from pathlib import Path
from medusa import Medusa, MedusaDesigner
import logging


#opens the webinterface for the designer and saves design to json
designer = MedusaDesigner()
designer.new_design()
exit()
input()


logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

