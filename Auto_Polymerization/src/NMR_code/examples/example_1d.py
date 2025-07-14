from matterlab_nmr import NMR60Pro, DSolv, HSolv
from pathlib import Path

base_path = Path(r"D:\Aspuru-Guzik Lab Dropbox\Lab Manager Aspuru-Guzik\PythonScript\Han\NanalysisNMR\nmr\examples")
nmr = NMR60Pro()

# for solvent system with deuterate solvent as locking
# nmr.set_regular_exp(num_scans=1, 
#                      solvent=DSolv.D2O, 
#                      spectrum_center=5, 
#                      spectrum_width=12,
#                      num_points=1024)
# shimming please do on 10% atom D or higher solvent, 1=three shimming para, 2=eight param, 3=30 param
#nmr.shim(2)


# for solvent system without deuterated solvent, try to lock free
nmr.set_hardlock_exp(num_scans=32, 
                     solvent=HSolv.DMSO, 
                     spectrum_center=5, 
                     spectrum_width=12
                     )


nmr.run()
nmr.proc_1D()
# nmr.display_spectrum()
nmr.save_spectrum(base_path, "0.2M_MMA,0.2M_Anisol_64scans_no_deutero_DMSO_test_2")
nmr.save_data(base_path, "0.2M_MMA,0.2M_Anisol_64scans_no_deutero_DMSO_test_2")