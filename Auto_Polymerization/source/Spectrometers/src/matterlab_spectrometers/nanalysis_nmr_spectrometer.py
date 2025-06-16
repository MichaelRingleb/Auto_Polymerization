import requests, time
import tempfile
import numpy as np
import json
from pathlib import Path
import matplotlib.pyplot as plt
from typing import List, Dict, Union, Optional, Tuple
from scipy.optimize import minimize
import nmrglue as ng
from enum import Enum, IntEnum
    
class NMRExperiment(IntEnum):
    UNKNOWN     = 0
    ONE_D       = 1
    NUTATION    = 2
    T1          = 3
    T2          = 4
    COSY        = 5
    JRES        = 6
    DEPT        = 7
    HSQC        = 8
    HMBC        = 9
    TOCSY       = 10
    KINETICS    = 11

class Nuclei(IntEnum):
    PROTON      = 0
    FLUORINE    = 1
    CARBON      = 2
    PROTON_HARD = 3

DEF_SPEC_PARAM = {
    Nuclei.PROTON: (5, 12),
    Nuclei.FLUORINE: (0, 400),
    Nuclei.CARBON: (100, 220),
    Nuclei.PROTON_HARD: (5, 12)
}

class DSolv(IntEnum):
    D2O         = 0
    DMSO_D6     = 1
    CDCL3       = 2
    CD3OD       = 3
    ACETONE_D6  = 4
    C6D6        = 5
    TFA_D       = 6
    C2D5OD      = 7
    C7D8        = 9
    THF_D8      = 10
    CD3CN       = 12
    CD2CL2      = 19

class HSolv(IntEnum):
    H2O         = 0
    DMSO        = 1
    CH3OH       = 2
    C6H6        = 3
    CHCL3       = 4
    GENERIC_1_P = 5
    GENERIC_2_P = 6
    GENERIC_3_P = 7
    DIOXANE     = 8

class ShimMethod(IntEnum):
    CANCEL      = 0
    QUICK       = 1
    MEDIUM      = 2
    FULL        = 3

class SuppressionMode(Enum):
    OFF = "Off"
    PRE_SAT = "Pre-Sat"
    DANTE = "DANTE"

class NMR60Pro(object):
    def __init__(self, url = 'http://nmr.matterlab.sandbox:5000'):
        self.base_url = url + '/interfaces/'
        self._attr_path = []
        self.raw_data = None
        self._check_connection()
        self._check_startup()
        self.get_shim_values()
        self.headers={}

    # call methods
    def fetch_json(self, res):
        if res.status_code == 200:
            return res.json()
        else:
            return {}

    def rest_get(self, path):
        res = requests.get(self.base_url+path)
        return self.fetch_json(res)

    def rest_put(self, path, data):
        res = requests.put(self.base_url+path, json = data)
        return self.fetch_json(res)

    # pipe methods
    def __getattr__(self, attr):
        self._attr_path.append(attr)
        return self

    def __call__(self, data = {}, **kwargs):
        # create url call path
        path = "/".join(self._attr_path)
        del self._attr_path[:]
        return self.call(path, data, **kwargs)

    def call(self, path, data = {}, **kwargs):
        req_data = data.copy()
        req_data.update(kwargs)
        if len(req_data.keys()) > 0:
            return self.rest_put(path, req_data)
        else:
            return self.rest_get(path)

    def set(self, **kwargs):
        return self.iFlow.ExperimentSettings(**kwargs)

    def get(self, *args):
        settings_dict = self.iFlow.ExperimentSettings()
        if len(args) == 0:
            return settings_dict
        elif len(args) == 1:
            return settings_dict.get(args[0], None)
        else:
            return [settings_dict.get(arg, None) for arg in args]

    # higher level experiment methods
    def idle(self):
        return self.iFlow.ExperimentStatus()['ResultCode'] == 0

    def run(self):
        self.iFlow.RunExperiment()
        while not self.idle():
            time.sleep(0.2)
        self.raw_data = self.iFlow.ExperimentStatus()['JDX_FileContents_TD']
        if self.raw_data:
            self._str2fids(self.raw_data)
        else:
            print("run failed")

    def shim(self, method: ShimMethod = ShimMethod.QUICK):
        self.iFlow.Shim({'ShimmingMethod': method, 'SolventShimming': False})
        while self.iFlow.Shim()['ShimmingMethod'] != 0:
            print(f"Shimming complete {self.iFlow.Shim()['PercentComplete']}")
            time.sleep(15)
        return self.resolution
    
    def get_shim_values(self)->List:
        self._shim_values = self.Service.ShimValues()["Shims"]
        return self._shim_values

    def set_shim_values(self, shims: Union[np.ndarray, List]):
        if isinstance(shims, np.ndarray):
            shims = shims.tolist()
        self.Service.ShimValues({"Shims": shims})

    def _str2fids(self, data: str):
        lines = [ln for ln in data.replace('\r', '').split('\n') if ln.strip()]
        tdeff: int = None
        facs: List = None
        zeroing: float = 0

        real_acc: np.ndarray = None
        imag_acc: np.ndarray = None
        cur_acc: np.ndarray = None

        headers_done: bool = False
        page_cnt: int = 0
        self._meta_data=[]
        for i, line in enumerate(lines):
            if "##END" in line:
                break

            if not headers_done:
                if line.startswith("##PAGE"):
                    headers_done = True
                    page_cnt = int(line.split("=")[-1])
                    tdeff = int(self.headers.get("$TDeff", 0))
                    facs = [float(x) for x in self.headers.get("FACTOR", "1,1,1,1").split(",")]
                    zeroing = float(self.headers.get("$ZEROING", 0))
                    real_acc = np.zeros(tdeff, float)
                    imag_acc = np.zeros(tdeff, float)
                    continue
                
                elif line.startswith("##") and "=" in line:
                    self._meta_data.append(line+"\n")
                    key, val = line[2:].split("=", 1)
                    self.headers[key] = val
                    if key == ".SHIFT REFERENCE":
                        parts = val.split(",")
                        if len(parts) >= 4:
                            self._reference_ppm = float(parts[3].strip())
                    elif key == "$PHASECORRECTION":
                        phases = [float(x) for x in val.split(",")]
                        if len(phases) >= 2:
                            self._initial_phases = (phases[0], phases[1])
                    elif key == "DELTAX":
                        self._dwell = float(val)
                    elif key == "$APODIZATION":
                        self._lb = float(val)
                    elif key == ".OBSERVE FREQUENCY":
                        self._obs_mhz = float(val)
                    elif key == "$O1":
                        self._o1_hz = float(val)
                    continue

                else:
                    continue
            
            if line.startswith("##DATA TABLE"):
                row_cnt = 0
                pts_per_row = 0
                if "(R..R)" in line:
                    cur_acc = real_acc
                    scale = facs[1] if len(facs) > 1 else 1.0
                elif "(I..I)" in line:
                    cur_acc = imag_acc
                    scale = facs[2] if len(facs) > 2 else 1.0
                else:
                    raise RuntimeError(f"Unknown DATA TABLE {line}")
                continue
            
            if cur_acc is not None:
                columns = np.array([float(x) for x in line.split()][1:])
                pts_per_row = columns.shape[0]
                cur_acc[row_cnt*pts_per_row: (row_cnt+1)*pts_per_row] = columns * scale
                row_cnt += 1

                if row_cnt * pts_per_row >= tdeff:
                    cur_acc = None
        if real_acc is None or imag_acc is None:
            raise ValueError("Failed to parse FID data")
        self._fid_raw = real_acc + 1j * imag_acc

    def _apply_apodization(self, fid: np.ndarray) -> np.ndarray:
        """Apply exponential line broadening to FID"""
        if self._lb <= 0:
            return fid
        t = np.arange(len(fid)) * self._dwell
        window = np.exp(-t * np.pi * self._lb)
        return fid * window

    def proc_1D(self, auto_phase = True, lb=0.1, ):
        N = self._fid_raw.size
        fid = self._fid_raw.copy()
        fid = self._apply_apodization(fid)
        self._spec = np.fft.fftshift(np.fft.fft(fid))
        self._freqs_hz = np.fft.fftshift(np.fft.fftfreq(N, d=self._dwell)) + self._o1_hz
        self._freqs_ppm = (self._freqs_hz / self._obs_mhz) #+ self.reference_ppm
        if auto_phase:
            self._spec = ng.proc_autophase.autops(self._spec, "acme")
        
    def save_data(self, dir: Path, base_name: str):
        with open(dir/f"{base_name}_raw.dx", "w") as f:
            f.write(self.raw_data)
        with open(dir/f"{base_name}_meta.out", "w") as f:
            f.writelines(self._meta_data)
        np.save(dir/f"{base_name}_spec.npy", self._spec)
        np.save(dir/f"{base_name}_freq_hz.npy", self._freqs_hz)
        np.save(dir/f"{base_name}_freq_ppm.npy", self._freqs_ppm)

    def _create_spectrum(self, title: str = "NMR spectrum", xlim: Optional[Tuple[float, float]] = None, **kwargs):
        fig, ax = plt.subplots(figsize=(8,6))
        ax.plot(self._freqs_ppm, np.real(self._spec), **kwargs)
        ax.invert_xaxis()
        if xlim is not None:
            ax.set_xlim(xlim[1], xlim[0])
        ax.set_title(title)
        ax.set_xlabel("Chemical shift (ppm)")
        ax.set_ylabel("Intensity")
        fig.tight_layout()
        return fig, ax
        
    def display_spectrum(self, title: str = "NMR spectrum", xlim: Optional[Tuple[float, float]] = None, **kwargs):
        fig, ax = self._create_spectrum(title=title, xlim=xlim, **kwargs)
        fig.show()

    def save_spectrum(self, dir: Path, base_name: str, title: str = "NMR spectrum", xlim: Optional[Tuple[float, float]] = None, **kwargs):
        fig, ax = self._create_spectrum(title=title, xlim=xlim, **kwargs)
        fig.savefig(dir/f"{base_name}.svg", format="svg")
        fig.savefig(dir/f"{base_name}.png")
        plt.close(fig)

    @property
    def rpc_enabled(self):
        return self.iStatus.RpcEnabled()["RpcEnabled"]

    @property
    def temperature_sensors(self):
        return self.iStatus.SpectrometerStatus()["Sensors"]
    
    @property
    def serial_number(self):
        return self.iStatus.SpectrometerStatus()["SerialNumber"]

    @property
    def software_version(self):
        return self.iStatus.SpectrometerStatus()["SoftwareVersion"]

    @property
    def spectrometer_freq(self):
        return self.iStatus.SpectrometerStatus()["SpectrometerFrequency"]
    
    @property
    def standby_mode(self):
        return self.iStatus.StandbyMode()["StandbyMode"]
    
    @property
    def resolution(self):
        return self.iStatus.SpectrometerStatus()['Resolution']['LineWidths']
    
    @standby_mode.setter
    def standby_mode(self, mode: bool):
        rtn = self.iStatus.StandbyMode({"StandbyMode": mode})["ResultCode"]
        time.sleep(1)
        if rtn or (self.standby_mode != mode):
            raise RuntimeError("Set standby mode failed!")

    @property
    def connected(self):
        return self.iStatus.PingSpectrometer()["connected"]
    
    def _check_connection(self):
        if self.connected:
            print("Spectrometer connected!")
        else:
            raise RuntimeError("Spectrometer not connected!")
        
    @property
    def startup_test(self):
        return self.iStatus.StartupTestStatus()

    def _check_startup(self):
        startup_status = self.startup_test
        if startup_status["ResultCode"] != 0:
            print(f"Spectrometer start up progress {startup_status['PercentComplete']}")
        else:
            print("Spectrometer start up finished.")

    def available_solvents(self)->Dict:
        return self.iStatus.Solvents()["SolventGroups"]
    
    def get_experiment_settings(self):
        return self.iFlow.ExperimentSettings()
    
    def set_regular_exp(self,
                        num_scans: int,
                        nuclei: Nuclei = Nuclei.PROTON,
                        solvent: DSolv = DSolv.CDCL3,
                        experiment: NMRExperiment = NMRExperiment.ONE_D,
                        spectrum_center: float | None = None,
                        spectrum_width: float | None = None,
                        num_points: int = 2048,
                        apodization: float = 0.2,
                        pulse_width_us: float = None,
                        receiver_gain: float = None,
                        scan_delay_s: float = None,
                        auto_baseline: bool = False,
                        auto_gain: bool = True,
                        auto_phase: bool = True,
                        pulse_angle: float = None,
                        suppresion: SuppressionMode | str = SuppressionMode.OFF,
                        suppression_length_ms: int = 500,
                        dante_total_presat_time_second: float = 1.5,
                        suppression_amplitude: int = 2,
                        dante_pulse_time_us: int = 10,
                        dante_interpulse_delay_us: int = 500,
                        dante_amplitude_factor: int = 80,
                        ):
        if nuclei == Nuclei.PROTON_HARD:
            print("For locking in 2H use set_hardlock_exp instead.")
            return
        default_center, default_width = DEF_SPEC_PARAM[nuclei]
        spectrum_center = spectrum_center if spectrum_center is not None else default_center
        spectrum_width = spectrum_width if spectrum_width is not None else default_width

        exp_setting = {
            "Apodization": apodization,
            "Experiment": experiment,
            "NumberOfPoints": num_points,
            "NumberOfScans": num_scans,
            "ScanDelayInSeconds": scan_delay_s,
            "SolventGroup": nuclei,
            "Solvent": solvent,
            "SpectralCentreInPpm": spectrum_center,
            "SpectralWidthInPpm": spectrum_width,

        }
        if pulse_width_us is not None:
            exp_setting["PulseWidthInMicroseconds"] = pulse_width_us
        if receiver_gain is not None:
            exp_setting["ReceiverGain"] = receiver_gain

        self.iFlow.ExperimentSettings(exp_setting)
        if experiment == NMRExperiment.ONE_D:
            self.set_1D_exp(auto_baseline=auto_baseline, auto_gain=auto_gain, auto_phase=auto_phase, pulse_angle=pulse_angle)

    def get_1D_exp_setting(self):
        rtn = requests.Session().get(f"{self.base_url}iFlow/Settings/1D")
        rtn.raise_for_status()
        return rtn.json()

    def set_1D_exp(self,
                   auto_baseline: bool = False,
                   auto_gain: bool = True,
                   auto_phase: bool = True,
                   pulse_angle: float = None
                   ):
        one_d_setting = self.get_1D_exp_setting()
        one_d_setting["AutoBaseline"] = auto_baseline
        one_d_setting["AutoGain"] = auto_gain
        one_d_setting["AutoPhase"] = auto_phase
        if pulse_angle is not None:
            one_d_setting["PulseAngle"] = pulse_angle
            one_d_setting["PulseWidth"] = -1

        rtn = requests.Session().put(f"{self.base_url}iFlow/Settings/1D", json=one_d_setting)
        rtn.raise_for_status()

    def set_hardlock_exp(self,
                         num_scans: int,
                         solvent: HSolv = HSolv.H2O,
                         experiment: NMRExperiment = NMRExperiment.ONE_D,
                         spectrum_center: float | None = None,
                         spectrum_width: float | None = None,
                         num_points: int = 2048,
                         apodization: float = 0.2,
                         pulse_width_us: float = None,
                         receiver_gain: float = None,
                         scan_delay_s: float = None,
                         ):
        default_center, default_width = DEF_SPEC_PARAM[Nuclei.PROTON_HARD]
        spectrum_center = spectrum_center if spectrum_center is not None else default_center
        spectrum_width = spectrum_width if spectrum_width is not None else default_width

        exp_setting = {
            "Apodization": apodization,
            "Experiment": experiment,
            "NumberOfPoints": num_points,
            "NumberOfScans": num_scans,
            "ScanDelayInSeconds": scan_delay_s,
            "SolventGroup": Nuclei.PROTON_HARD,
            "Solvent": solvent,
            "SpectralCentreInPpm": spectrum_center,
            "SpectralWidthInPpm": spectrum_width,

        }
        if pulse_width_us is not None:
            exp_setting["PulseWidthInMicroseconds"] = pulse_width_us
        if receiver_gain is not None:
            exp_setting["ReceiverGain"] = receiver_gain

        self.iFlow.ExperimentSettings(exp_setting)

    def cancel_experiment(self):
        self.iFlow.CancelExperiment()

    
