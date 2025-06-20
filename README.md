# Auto_Polymerization




## Required packages and installation
Thorlabs Drivers for CCS200 spectrometer: https://www.thorlabs.com/thorproduct.cfm?partnumber=CCS200#ad-image-0 
#Thorlabs Driver for upLED controller: https://wmit CHatGPT programmiert, dasww.thorlabs.com/thorproduct.cfm?partnumber=UPLED 

python == 3.10


scipy, numpy, pandas, matplotlib, pyserial, nmrglue, requests, pyserial,pyyaml

from matterlab:
https://gitlab.com/aspuru-guzik-group/self-driving-lab/devices
Hotplates
Pumps
Spectrometer 
Serial Device

Install Arduino IDE on PC and upload the Arduino code (in subfolder Arduino sketch) to the Arduino board


For correct DLL for CSS200 spectrometer, you have to change the value for DLL_FILE in ccs_spectrometer.py in the matterlab package.
The correct file path is typically DLL_FILE = Path(r"C:\Program Files\IVI Foundation\VISA\Win64\Bin\TLCCS_64.dll")

## Notes
- Adjust the COM port (`port="COM7"`) to match your system.
- The methods and properties of the `IKARETControlVisc` class are defined in `Stirrer/IKA_RET_Control_Visc.py`.
- For further examples, see the script `Auto_Polymerization/hot_stir_plate.py`.

## Development

If you want to develop the package further, use the development mode (`pip install -e .`). Changes to the source code will be picked up immediately.

## License
MIT License (or specify your own license here)

---

**Questions or issues?**  
Please open an issue on GitHub or contact the maintainers.
