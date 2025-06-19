# -*- coding: utf-8 -*-

import os
import glob
import numpy as np
import matplotlib.pyplot as plt


# -*- coding: utf-8 -*-

import os
import glob
import numpy as np
import matplotlib.pyplot as plt


def plot_spectra():
    # Nur im Ordner "spectra" suchen, nicht in Unterordnern
    spectra_dir = os.path.join(os.path.dirname(__file__), "spectra")
    txt_files = glob.glob(os.path.join(spectra_dir, "*.txt"))  # kein "**", also keine Unterordner

    print("Gefundene Spektren:", txt_files)

    plt.figure(figsize=(10, 6))

    for file in txt_files:
        try:
            data = np.loadtxt(file, comments='#', delimiter=None)
            if data.ndim < 2 or data.shape[1] < 2:
                continue
            x = data[:, 0]
            y = data[:, 1]
            plt.plot(x, y, label=os.path.basename(file))
        except Exception as e:
            print(f"Fehler beim Laden von {file}: {e}")

    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title("Alle Spektren aus TXT-Dateien")
    plt.legend(fontsize='small', loc='best')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_spectra()