import time
from ctypes import *
from pathlib import Path
import json

DLL_FILE = Path.cwd().parent.parent/"dll"/"PM100D_DLL"/"PM100D_64.dll"

class PM100DPowermeter(object):
    def __init__(self,
                 ):
        self._load_dll()
        self._instrument_handle=c_int(0)
        self._find_resources()
        self.resource_name
        self._initialized = False
        self.initialize(id_query=True, reset_device=True)



    def _load_dll(self):
        print(DLL_FILE)
        assert DLL_FILE.exists(), "Spectrometer DLL path is wrong, check!"
        self.lib = cdll.LoadLibrary(str(DLL_FILE))
        # assert DLL_FILE.exists(), "Spectrometer DLL path is wrong, check!"
        # self.lib = cdll.LoadLibrary(str(Path.cwd().parent.parent/'dll'/'PM100D_DLL'/'PM100D_64.dll'))

    def _find_resources(self):
        """
        find the number of devices connected, MUST run BEFORE the initialization of device
        :return:
        """
        device_count = c_int(0)
        rtn = self.lib.PM100D_findRsrc(self._instrument_handle, byref(device_count))
        if rtn != 0:
            raise IOError("Find resource number failed")
        if device_count.value:
            print(f"Number of devices connected is {device_count.value}")
        else:
            raise IOError("No device found!")

    @property
    def resource_name(self, device_count: int = 0)->str:
        """
        get the resource name of the device, MUST run right after find resources
        :return:
        """
        self._resource_name = create_string_buffer(256)
        rtn = self.lib.PM100D_getRsrcName(self._instrument_handle, c_int(device_count), self._resource_name)
        if rtn != 0:
            raise IOError("Get resource name failed!")
        print(f"Resource name is {self._resource_name.value.decode('utf-8')}")
        return self._resource_name.value.decode('utf-8')

    def initialize(self, id_query:bool = True, reset_device: bool= True):
        """
        initialize device, call after get resource name
        :param id_query: if query the id
        :param reset_device: if reset the device
        :return:
        """
        rtn = self.lib.PM100D_init(self._resource_name,
                                   c_bool(id_query),
                                   c_bool(reset_device),
                                   byref(self._instrument_handle)
                                   )
        if rtn != 0:
            raise IOError("Initialization failed!")
        self._initialized = True

    def close(self):
        """
        close the communication, does not close the instrument electronically
        :return:
        """
        if self._initialized:
            self.lib.PM100D_close(self._instrument_handle)
            self._initialized = False
            print("Instrument communication closed")
        else:
            print("Instrument communication is already closed")

    @property
    def calibration_message(self)->str:
        """
        get the calibration date
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._calibration_message = create_string_buffer(256)
        rtn = self.lib.PM100D_getCalibrationMsg(self._instrument_handle, self._calibration_message)
        if rtn != 0:
            print("Get calibration message failed")
            return
        print(f"Calibration date is {self._calibration_message.value.decode()}")
        return self._calibration_message.value.decode()

    @property
    def wavelength(self)->float:
        """
        get the measure wavelength
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._wavelength = c_double()
        rtn = self.lib.PM100D_getWavelength(self._instrument_handle, c_int16(0), byref(self._wavelength))
        if rtn != 0:
            raise IOError("Get wavelength set failed")
        print(self._wavelength.value)
        return self._wavelength.value

    @property
    def wavelength_min(self) -> float:
        """
        get the min wavelength
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._wavelength_min = c_double()
        rtn = self.lib.PM100D_getWavelength(self._instrument_handle, c_int16(1), byref(self._wavelength_min))
        if rtn != 0:
            raise IOError("Get wavelength min failed")
        print(self._wavelength_min.value)
        return self._wavelength_min.value

    @property
    def wavelength_max(self) -> float:
        """
        get the max wavelength
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._wavelength_max = c_double()
        rtn = self.lib.PM100D_getWavelength(self._instrument_handle, c_int16(2), byref(self._wavelength_max))
        if rtn != 0:
            raise IOError("Get wavelength max failed")
        print(self._wavelength_max.value)
        return self._wavelength_max.value

    @wavelength.setter
    def wavelength(self, wavelength: float):
        """
        set the central wavelength
        :param wavelength:
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        rtn = self.lib.PM100D_setWavelength(self._instrument_handle, c_double(wavelength))
        if rtn != 0:
            raise IOError("Set central wavelength failed")

    @property
    def power_autorange(self)->int:
        """
        query if the power measurement is using autoranging
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._power_auto_range = c_uint16()
        rtn = self.lib.PM100D_getPowerAutorange(self._instrument_handle, byref(self._power_auto_range))
        if rtn != 0:
            raise IOError("Get power auto range failure")
        if self._power_auto_range.value:
            print("Power auto range ON")
        else:
            print("Power auto range OFF")
        return self._power_auto_range.value

    @power_autorange.setter
    def power_autorange(self, autorange: bool):
        """
        set to turn autorange on or off for power measurement
        :param autorange:
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        rtn = self.lib.PM100D_setPowerAutoRange(self._instrument_handle, c_uint16(autorange))
        if rtn != 0:
            raise IOError("Set power measurement autorange failed")

    @property
    def power_range(self)->float:
        """
        get the power range currently at
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._power_range = c_double()
        rtn = self.lib.PM100D_getPowerRange(self._instrument_handle, c_int16(0), byref(self._power_range))
        if rtn != 0:
            raise IOError("Get current power range failed")
        print(f"Power range is {self._power_range.value:.3E} W")
        return self._power_range

    @property
    def power_range_min(self) -> float:
        """
        get the power range min
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._power_range_min = c_double()
        rtn = self.lib.PM100D_getPowerRange(self._instrument_handle, c_int16(1), byref(self._power_range_min))
        if rtn != 0:
            raise IOError("Get min power range failed")
        print(f"Power range is {self._power_range_min.value:.3E} W")
        return self._power_range_min

    @property
    def power_range_max(self) -> float:
        """
        get the power range currently at
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._power_range_max = c_double()
        rtn = self.lib.PM100D_getPowerRange(self._instrument_handle, c_int16(2), byref(self._power_range_max))
        if rtn != 0:
            raise IOError("Get max power range failed")
        print(f"Power range is {self._power_range_max.value:.3E} W")
        return self._power_range_max

    @power_range.setter
    def power_range(self, power_range: float):
        """
        set the power range to use.
        BECAREFUL, may damage probe!
        :param power_range:
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        print(
            "#################################################################\n"
            "##########                                             ##########\n"
            "##########       Only for careful manual tuning        ##########\n"
            "##########          Use autorange if possible          ##########\n"
            "##########             Type Yes to confirm             ##########\n"
            "##########                                             ##########\n"
            "#################################################################\n"
        )
        # if input() != "Yes":
        #     print("Quit manual adjust power range.")
        #     return
        # power_range_c = c_double(power_range)
        # power_range_c = c_double(0.0001)
        rtn = self.lib.PM100D_setPowerRange(self._instrument_handle, c_double(power_range))
        # if rtn != 0:
        #     raise IOError("Set power range failed")
        # ATTN
        # Error handling is omitted here since it return failed even the setting was correct
        # Check the screen for actual values

    @property
    def power(self)->float:
        """
        measure optic power
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._power = c_double()
        rtn = self.lib.PM100D_measPower(self._instrument_handle, byref(self._power))
        if rtn != 0:
            raise IOError("Measure power failed!")
        print(f"Power is {self._power.value:.3E} W")
        return self._power.value

    def error_query(self):
        """
        Query the error
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        error_num = c_int()
        error_message = create_string_buffer(256)
        self.lib.PM100D_errorQuery(self._instrument_handle, error_num, error_message)
        print(f"Error number {error_num}\nError message {error_message}")

    @property
    def average_count(self)->int:
        """
        get the average count of measurement
        :return:
        """
        assert self._initialized, "Instrument not initialized"
        self._average_count = c_int16(0)
        rtn = self.lib.PM100D_getAvgCnt(self._instrument_handle, )

# pm = PM100DPowermeter()
# pm.initialize()
# pm.close()
# pm.get_calibration_message
# pm.wavelength_set
# pm.wavelength_min
# pm.wavelength_max
# pm.wavelength_set=800
# pm.power_autorange
# pm.power_autorange = 0
# pm.power_autorange
# pm.power_range
# pm.power_range_min
# pm.power_range_max
# pm.power_range = 1e-6
# time.sleep(5)
# for i in range(0, 10):
#     pm.power