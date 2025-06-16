import time
from ctypes import *
from pathlib import Path
import json
import numpy as np
from typing import List
from numpy.typing import NDArray

# DLL_FILE = Path(r"C:\Program Files\IVI Foundation\VISA\Win64\Bin\TLCCS_64.dll")
# DLL_FILE = Path.cwd().parent.parent/"dll"/"CCS_DLL"/"TLCCS_64.dll"

DLL_FILE = Path(__file__).parent.parent/"dll"/"CCS_DLL"/"TLCCS_64.dll"
CCS_DEV_MODEL = {
    "CCS100": "0x8081",
    "CCS125": "0x8083",
    "CCS150": "0x8085",
    "CCS175": "0x8087",
    "CCS200": "0x8089"
}


class CCSSpectrometer(object):
    def __init__(self,
                 usb_port: str = "USB0",
                 device_model: str = "CCS200",
                 device_id: str = "M00802700",
                 num_pixel: int = 3648
                 ):
        self._load_dll()
        self.initialize_instrument(usb_port, device_model, device_id)
        self._integration_time = 0
        self.integration_time = 1e-1
        self._instrument_status = 0x0000
        self.num_pixel = num_pixel


    def _load_dll(self):
        print(DLL_FILE)
        assert DLL_FILE.exists(), "Spectrometer DLL path is wrong, check!"
        self.lib = cdll.LoadLibrary(str(DLL_FILE))
        # self.lib = cdll.LoadLibrary(str(Path.cwd().parent.parent/'dll'/'TLCCS_64.dll'))
        # self.lib = cdll.LoadLibrary(str(Path(r"C:\Users\han\Aspuru-Guzik Lab Dropbox\Hao Han\PythonScript\Han\Spectrometer\Spectrometer\dll\CCS_DLL\TLCCS_64.dll")))

    def initialize_instrument(self, usb_port, device_model, device_id, id_query: bool = True, reset_device: bool = True):
        """
        initialize the instrument, get the instrument handle as self.instrument_handle
        :return:
        """
        resource_name = f"{usb_port}::0x1313::{CCS_DEV_MODEL[device_model]}::{device_id}::RAW".encode()
        # id_query = c_int16(1)
        # reset_device = 1
        self._instrument_handle = c_ulong(0)
        rtn = self.lib.tlccs_init(resource_name,
                                  c_uint16(int(id_query)),
                                  c_uint16(int(reset_device)),
                                  byref(self._instrument_handle)
                                  )
        if rtn != 0:
            raise IOError(f"Instrument initialization failed with error code {rtn}")

    def close_instrument(self):
        """
        close instrument
        :return:
        """
        rtn = self.lib.tlccs_close(self._instrument_handle)
        if rtn != 0:
            raise IOError(f"Instrument close failed with error code {rtn}")

    def reset(self):
        """
        reset the instrument
        :return:
        """
        rtn = self.lib.tlccs_reset(self._instrument_handle)
        if rtn != 0:
            raise IOError(f"Instrument reset failed with error code {rtn}")

    def self_test(self):
        """
        perform self test
        :return:
        """
        raise NotImplementedError("self_test in TLCSS_64.dll does not work, and selfTest is not there")
        # self_test_result = c_int()
        # self_test_message = create_string_buffer(256)
        # rtn = self.lib.tlccs_selfTest(self._instrument_handle,
        #                               byref(self_test_result),
        #                               self_test_message
        #                               )
        # if rtn != 0:
        #     raise IOError(f"Instrument self test failed with error code {rtn}")
        # print("Test result is \n", self_test_result.value)
        # print("Test message is \n", self_test_message.value.decode('utf-8'))

    def error_query(self):
        """
        query for errors
        :return:
        """
        # TODO testing of error query
        error_number = c_int()
        error_message = create_string_buffer(256)
        self.lib.tlccs_errorQuery(self._instrument_handle,
                                  byref(error_number),
                                  error_message
                                  )
        print("Error number is \n", error_number.value)
        print("Error message is \n", error_message.value.decode('utf-8'))

    @property
    def integration_time(self):
        """
        get the integration time of the instrument in seconds
        :return:
        """
        integration_time = c_double(0)
        rtn = self.lib.tlccs_getIntegrationTime(self._instrument_handle, byref(integration_time))
        if rtn != 0:
            print(f"Get integration failed with error code {rtn}")
            return
        self._integration_time = integration_time.value
        print(f"Integration time is {self._integration_time} s!")
        return self._integration_time

    @integration_time.setter
    def integration_time(self, integration_time: float):
        """
        set the integration time of the instrument
        :param integration_time: integration time in seconds
        :return:
        """
        if integration_time < 1e-5:
            integration_time = 1e-5
            print("Integration time too short, set to min as 1e-5 s!")
        if integration_time > 6e1:
            integration_time = 6e1
            print("Integration time too long, set to max as 6e1!")
        rtn = self.lib.tlccs_setIntegrationTime(self._instrument_handle, c_double(integration_time))
        if rtn != 0:
            print(f"Set integration failed with error code {rtn}")
            return
        time.sleep(1)
        # if self.integration_time != integration_time:
        # it won't work for long integration time due to float errors, below is implemented then
        # if self.integration_time not in range(0.99 * integration_time, 1.01 * integration_time):
        #     raise IOError("Integration time setting failed!")

    @property
    def instrument_status(self):
        """
        get the instrument status
        :return:
        """
        # TODO testing of getting instrument status!
        instrument_status = c_int(0)
        rtn = self.lib.tlccs_getDeviceStatus(self._instrument_handle, byref(instrument_status))
        if rtn != 0:
            print(f"Get instrument status failed with error code {rtn}")
            return
        self._instrument_status = instrument_status.value
        if self._instrument_status == 0x0002:
            print("IDLE, instrument waits for new scan")
        elif self._instrument_status == 0x0004:
            print("TRIGGERED, scan in progress")
        elif self._instrument_status == 0x0008:
            print("START_TRANS, scan starting")
        elif self._instrument_status == 0x0010:
            print("TRANSFER, scan done wait for data transfer")
        elif self._instrument_status == 0x0080:
            print("EXT_TRIG, instrument waits for external trigger")
        return self._instrument_status

    def start_scan(self):
        """
        start scan
        :return:
        """
        rtn = self.lib.tlccs_startScan(self._instrument_handle)
        if rtn != 0:
            print(f"Start one scan failed with error code {rtn}")
            return

    def start_scan_continuous(self):
        """
        start scan continuously, will be stopped by get_scan_data
        :return:
        """
        rtn = self.lib.tlccs_startScanCont(self._instrument_handle)
        if rtn != 0:
            print(f"Start continuous scan failed with error code {rtn}")
            return

    def start_scan_external_trigger(self):
        """
        start scan after an external trigger
        :return:
        """
        rtn = self.lib.tlccs_startScanExtTrg(self._instrument_handle)
        # ATTN does this apply?
        if rtn != 0:
            print(f"Start one scan with external trigger failed with error code {rtn}")
            return

    def start_scan_continuous_external_trigger(self):
        """
        start scan continuously after an external trigger, will be stopped by get_scan_data
        :return:
        """
        rtn = self.lib.tlccs_startScanContExtTrg(self._instrument_handle)
        # ATTN does this apply?
        if rtn != 0:
            print(f"Start continuous scan with external trigger failed with error code {rtn}")
            return

    def get_sensor_data(self):
        """
        read the processed scan data and return
        will break all current continuous scan
        readings will be set to all 0.0 if overexposure
        :return: scan data as np 1d array
        """
        data_array = (c_double * self.num_pixel)()
        rtn = self.lib.tlccs_getScanData(self._instrument_handle, byref(data_array))
        if rtn != 0:
            print(f"Get processed scan data failed with error code {rtn}")
            return
        return np.array(data_array)

    def get_raw_scan_data(self):
        """
        read the raw scan data and return
        will break all current continuous scan
        :return:
        """
        data_array = (c_double * self.num_pixel)()
        rtn = self.lib.tlccs_getRawScanData(self._instrument_handle, byref(data_array))
        if rtn != 0:
            print(f"Get raw scan data failed with error code {rtn}")
            return
        return np.array(data_array)

    def get_wavelength_data(self, user_setting: bool = False):
        """
        read the wavelength per pixel
        :return:
        """
        # TODO test of get wavelength
        use_user_setting = c_int(int(user_setting))
        wavelength_array = (c_double * self.num_pixel)()
        wavelength_min = c_double(0)
        wavelength_max = c_double(0)

        rtn = self.lib.tlccs_getWavelengthData(self._instrument_handle,
                                               c_bool(use_user_setting),
                                               # byref(use_user_setting),
                                               byref(wavelength_array),
                                               byref(wavelength_min),
                                               byref(wavelength_max)
                                               )
        if rtn != 0:
            print(f"Get wavelength data failed with error code {rtn}")
            return
        self.wavelength_data = np.array(wavelength_array)
        return self.wavelength_data

    def set_wavelength_data(self, pixels: List, wavelengths: List, confirmation: bool = True):
        """
        create the calibration based on pixel-wavelength correlation
        :param confirmation:
        :param pixels:
        :param wavelengths:
        :return:
        """
        assert len(pixels) == len(wavelengths), "Number of pixels must be same as number of wavelengths"
        assert 4 <= len(pixels) <= 10, "4 <= Number of pixels <= 10"
        assert 4 <= len(wavelengths) <= 10, "4 <= Number of wavelengths <= 10"
        buffer_length = c_int(len(pixels))
        pixels_array = (c_int * buffer_length)()
        wavelengths_array = (c_int * buffer_length)()
        for i in range(0, buffer_length):
            pixels_array[i] = pixels[i]
            wavelengths_array[i] = wavelengths[i]

        rtn = self.lib.tlccs_setWavelengthData(self._instrument_handle,
                                               byref(buffer_length),
                                               byref(wavelengths_array),
                                               byref(pixels_array)
                                               )
        if rtn != 0:
            print(f"Set wavelength data failed with error code {rtn}")
            return
        if confirmation:
            self.get_wavelength_data()
            if self.wavelength_data != np.array(wavelengths):
                raise IOError("Updating wavelength calibration failed")

    def get_user_calibration_points(self):
        """
        get the user defined calibration points
        :return:
        """
        pixels_array = (c_int * 10)()
        wavelengths_array = (c_int * 10)()
        buffer_length = c_int()
        rtn = self.lib.tlccs_getUserCalibrationPoints(self._instrument_handle,
                                                      byref(pixels_array),
                                                      byref(wavelengths_array),
                                                      byref(buffer_length)
                                                      )
        if rtn != 0:
            print(f"Get user calibration points failed with error code {rtn}")
            return
        return np.vstack((np.array(pixels_array), np.array(wavelengths_array)))

    def get_amplitude_data(self, buffer_start: int, buffer_length: int, amplitudes: NDArray[np.float16],
                           read_nonvolatile: bool = False):
        """
        get the amplitude data per pixel
        :param buffer_start:
        :param buffer_length:
        :param amplitudes:
        :param read_nonvolatile: if read from the non-volatile memory
        :return:
        """
        assert buffer_start + buffer_length < self.default_settings['num_pixel'][
            0], "Writing pixel not exceed pixel length"
        buffer_start_c = c_int(buffer_start)
        buffer_length_c = c_int(buffer_length)
        if read_nonvolatile:
            mode = c_int(2)
        else:
            mode = c_int(1)
        amplitudes_array = (c_double * buffer_length)()
        for i in range(0, buffer_length):
            amplitudes_array[i] = amplitudes[i]
        rtn = self.lib.tlccs_getAmplitudeData(self._instrument_handle,
                                              byref(amplitudes_array),
                                              buffer_start_c,
                                              buffer_length_c, mode
                                              )
        if rtn != 0:
            print(f"Get amplitude data failed with error code {rtn}")
            return
        return np.array(amplitudes_array)

    def set_amplitude_data(self, buffer_start: int, buffer_length: int, amplitudes: NDArray[np.float16],
                           write_nonvolatile: bool = False):
        """
        set the amplitude data per pixel
        :param buffer_start:
        :param buffer_length:
        :param amplitudes:
        :param write_nonvolatile: if write to the non-volatile memory
        :return:
        """
        assert buffer_start + buffer_length < self.default_settings['num_pixel'][
            0], "Writing pixel not exceed pixel length"
        buffer_start_c = c_int(buffer_start)
        buffer_length_c = c_int(buffer_length)
        if write_nonvolatile:
            print("#################################################################\n"
                  "##########                                             ##########\n"
                  "##########  Are you sure overwrite non volatile mem?   ##########\n"
                  "##########  Consider set write_nonvolatile to False.   ##########\n"
                  "##########            Type Yes to confirm              ##########\n"
                  "##########                                             ##########\n"
                  "#################################################################\n"
                  )
            if input() == "Yes":
                mode = c_int(2)
            else:
                print("Quit write non-volatile memory.")
                return
        else:
            mode = c_int(1)
        amplitudes_array = (c_double * buffer_length)()
        for i in range(0, buffer_length):
            amplitudes_array[i] = amplitudes[i]
        rtn = self.lib.tlccs_setAmplitudeData(self._instrument_handle,
                                              byref(amplitudes_array),
                                              buffer_start_c,
                                              buffer_length_c,
                                              mode)
        if rtn != 0:
            print(f"Set amplitude data failed with error code {rtn}")
            return

    def identification_query(self):
        """
        query the identification of the instrument
        :return:
        """
        manufacture_name = create_string_buffer(256)
        device_name = create_string_buffer(256)
        serial_number = create_string_buffer(256)
        firmware_revision = create_string_buffer(256)
        instrument_driver_revision = create_string_buffer(256)

        rtn = self.lib.tlccs_identificationQuery(self._instrument_handle,
                                                 manufacture_name,
                                                 device_name,
                                                 serial_number,
                                                 firmware_revision,
                                                 instrument_driver_revision
                                                 )
        if rtn != 0:
            print(f"Identification query failed with error code {rtn}")
            return
        self._identification = {
            "manufacture_name": manufacture_name.value.decode('utf-8'),
            "device_name": device_name.value.decode('utf-8'),
            "serial_number": serial_number.value.decode('utf-8'),
            "firmware_revision": firmware_revision.value.decode('utf-8'),
            "instrument_driver_revision": instrument_driver_revision.value.decode('utf-8'),
        }
        return self._identification

    def measure_spectrum(self, integration_time: float)->np.ndarray:
        """
        measure the spectrum
        :param integration_time:
        :return:
        """
        self.integration_time = integration_time
        self.start_scan()
        return self.get_sensor_data()