from ctypes import *
from pathlib import Path

DLL_FILE = Path.cwd().parent.parent/"dll"/"PM16X_DLL"/"PM100D_64_dll"

PM_DEV_MODEL={
    "PM16-120": "0x807B"
}
class PM16XPowermeter(object):
    def __init__(self,
                 usb_port: str = "USB0",
                 device_model: str = "PM16-120",
                 device_id: str = "220201226"
                 ):
        self._load_dll()
        self.initialize_instrument(usb_port, device_model, device_id)

    def _load_dll(self):
        print(DLL_FILE)
        assert DLL_FILE.exists(), "Spectrometer DLL path is wrong, check!"
        self.lib = cdll.LoadLibrary(str(DLL_FILE))
        # self.lib = cdll.LoadLibrary(str(Path.cwd().parent.parent/'dll'/'PM160_64.dll'))
        # self.lib = cdll.LoadLibrary(str(Path(
        #     r"C:\Users\han\Aspuru-Guzik Lab Dropbox\Hao Han\PythonScript\Han\Spectrometer\Spectrometer\dll\PM16X_DLL\PM100D_64.dll")))

    def initialize_instrument(self, usb_port, device_model, device_id, id_query: bool = True,
                              reset_device: bool = True):
        """
        initialize the instrument, get the instrument handle as self.instrument_handle
        :return:
        """
        resource_name = f"{usb_port}::0x1313::{PM_DEV_MODEL[device_model]}::{device_id}::INSTR".encode()
        self._instrument_handle = c_ulong(0)
        rtn = self.lib.PM100D_init(resource_name,
                                  c_uint16(int(id_query)),
                                  c_uint16(int(reset_device)),
                                  byref(self._instrument_handle)
                                  )
        if rtn != 0:
            raise IOError(f"Instrument initialization failed with error code {rtn}")

    def close(self):
        """
        close communication with instrument
        :return:
        """
        rtn = self.lib.PM100D_close(self._instrument_handle)
        if rtn != 0:
            raise IOError("Close instrument communication failed")

    def error_query(self):
        """
        query the errors
        :return:
        """
        # TODO long PM100D_errorQuery(unsigned long instr, long *pNum, char *msg);
        raise NotImplementedError("Error query to be implemented")

    @property
    def power(self)->float:
        """
        measure the power
        :return:
        """
        power = c_double()
        rtn = self.lib.PM100D_measPower(self._instrument_handle, byref(power))
        if rtn != 0:
            raise IOError("Measure power failed!")
        print(f"Power measured is {power.value} W")
        return power.value

    @property
    def power_range(self)->float:
        """
        get the power range of measurement
        :param get_default:
        :return:
        """
        self._power_range = c_double()
        rtn = self.lib.PM100D_getPowerRange(self._instrument_handle, c_int16(0), byref(self._power_range))
        if rtn != 0:
            raise IOError("Get power range failed")
        print(f"Power range is {self._power_range.value:.2E} W")
        return self._power_range.value

# pm = PM16XPowermeter()