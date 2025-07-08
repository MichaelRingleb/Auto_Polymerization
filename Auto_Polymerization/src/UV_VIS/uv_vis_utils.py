#controls the uv_vis measurements 
import sys
import os
import time
import serial
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
from matterlab_spectrometers.ccs_spectrometer import CCSSpectrometer

#definition of the spectrometer
spec = CCSSpectrometer(
        usb_port="USB",
        device_model="CCS200",
        device_id="M00479664"
    )

#definition of integration time (default is 3 ms)
integration_time = 0.003

#function to take a spectrum and save it
def take_spectrum(baseline = False, t0 = False):
    spectrum = spec.measure_spectrum(integration_time)
    wavelengths = spec.get_wavelength_data()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"UV_VIS_spectrum_{timestamp}.txt"
    save_spectrum(wavelengths, spectrum, timestamp, filename, baseline, t0)
    return spectrum, wavelengths, filename


#function to save the spectrum to corresponding folder
def save_spectrum(wavelengths, spectrum, timestamp, filename=None, baseline = False, t0 = False):
    # Get the project root (assuming this script is in Auto_Polymerization/src/UV_VIS/)
    project_root = Path(__file__).resolve().parents[3]
    spectra_folder = project_root / "users" / "data" / "UV_VIS_data"
    spectra_folder.mkdir(parents=True, exist_ok=True)
    
    if baseline == True:
        filename = f"UV_VIS_baseline_spectrum_{timestamp}.txt"

    if t0 == True:
        filename = f"UV_VIS_t0_spectrum_{timestamp}.txt"

    if filename is None:
        filename = f"UV_VIS_spectrum_{timestamp}.txt"
   
    file_path = spectra_folder / filename

    data = np.column_stack((wavelengths, spectrum))
    np.savetxt(file_path, data, header="Wavelength (nm)\tIntensity (a.u.)", fmt="%.4f\t%.6f")

    print(f"Spectrum saved to {file_path}")
    return file_path

def subtract_baseline(spectrum, baseline_spectrum):
    #search in data folder for the baseline spectrum
    project_root = Path(__file__).resolve().parents[3]
    baseline_folder = project_root / "users" / "data" / "UV_VIS_data"
    #search in baseline_folder for the baseline spectrum by the substring "baseline"
    baseline_files = [f for f in os.listdir(baseline_folder) if "baseline" in f]
    #load the baseline spectrum
    baseline_spectrum = np.loadtxt(baseline_folder / baseline_files[0])
    #for the spectrum, subtract intensity of  the baseline spectrum at a certain wavelength from the intensity of the spectrum at the same wavelength
    #find the index of the wavelength in the baseline spectrum (using numpy operations)
    index = np.where(baseline_spectrum[:, 0] == spectrum[i, 0])
   
    else:
        print(f"Wavelength {spectrum[i, 0]} not found in baseline spectrum")


    """
    for i in range(len(spectrum)):
        index = np.where(baseline_spectrum[:, 0] == spectrum[i, 0])
        if len(index) > 0:
            spectrum[i] = spectrum[i] - baseline_spectrum[index, 1]
        else:
            print(f"Wavelength {spectrum[i, 0]} not found in baseline spectrum")
"""



def calculate_absorbance(spectrum, reference_spectrum):


# function to calculate the absorbance from the saved spectrum
def calculate_absorbance(spectrum, reference_spectrum):
    #calculate the absorbance from the saved spectrum


def plot_spectrum(wavelengths, spectrum, title):
    plt.figure()
    plt.plot(wavelengths, spectrum)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title(title)
    plt.grid(True)
    #plt.show(block=False)  # show non-blocking so the loop can continue
