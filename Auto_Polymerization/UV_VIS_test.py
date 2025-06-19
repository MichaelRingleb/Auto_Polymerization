import sys
import os
import time
import serial
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from matterlab_pumps.longer_peri import LongerPeristalticPump
from matterlab_spectrometers.ccs_spectrometer import CCSSpectrometer

def save_spectrum(wavelengths, spectrum, filename):
    data = np.column_stack((wavelengths, spectrum))
    np.savetxt(filename, data, header="Wavelength (nm)\tIntensity (a.u.)", fmt="%.4f\t%.6f")

def plot_spectrum(wavelengths, spectrum, title):
    plt.figure()
    plt.plot(wavelengths, spectrum)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title(title)
    plt.grid(True)
    #plt.show(block=False)  # show non-blocking so the loop can continue

def pump_spectrum_loop():
    pump = LongerPeristalticPump(com_port="COM16", address=1)
    spec = CCSSpectrometer(
        usb_port="USB",
        device_model="CCS200",
        device_id="M00479664"
    )
    try:
        i = 1
        while True:
            print(f"--- Loop {i}: Starting pump for 300 seconds ---")
            pump.set_pump(rpm=0.7, on=True, direction=False)
            time.sleep(300) 
            print("Stopping pump and taking spectrum...")
            pump.set_pump(on=False)
            time.sleep(2)  # short wait to ensure flow stops
            spectrum = spec.measure_spectrum(0.1)
            wavelengths = spec.get_wavelength_data()
            # filename with date and datetime
            now = datetime.now()
            filename = now.strftime("spectrum_%Y-%m-%d_%H-%M-%S.txt")
            save_spectrum(wavelengths, spectrum, filename)
            print(f"Spectrum saved as {filename}")
            plot_spectrum(wavelengths, spectrum, f"Spectrum {i} ({now.strftime('%Y-%m-%d %H:%M:%S')})")
            i += 1
            print("Restarting pump...")
            pump.set_pump(rpm=0.7, on=True, direction=False)
            time.sleep(2)  # short wait before next loop
    except KeyboardInterrupt:
        print("Loop interrupted by user. Stopping pump and closing spectrometer.")
        pump.set_pump(on=False)
        spec.close_instrument()

if __name__ == "__main__":
    pump_spectrum_loop()