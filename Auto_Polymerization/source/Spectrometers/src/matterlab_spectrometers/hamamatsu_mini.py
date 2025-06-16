import ctypes
from ctypes import wintypes, c_void_p, c_ushort,c_uint, c_byte, c_double, c_char_p, POINTER, byref, WinDLL
from pathlib import Path
from enum import Enum
import numpy as np
from typing import Dict, Tuple, List, Optional, Union
import time
from math import ceil

class USBDevReturnCode(Enum):
    INVALID_HANDLE_VALUE = -1
    USBDEV_SUCCESS = 0
    USBDEV_INVALID_HANDLE = 1
    USBDEV_UNSUCCESS = 2
    USBDEV_INVALID_VALUE = 3
    USBDEV_INVALID_PARAMETER = 4
    USBDEV_CHECK_NORMAL = 11
    USBDEV_CHECK_INVALID = 12
    USBDEV_CHECK_REMOVE = 13
    USBDEV_BULK_SIZE_ERROR = 20
    USBDEV_BULK_READ_ERROR = 21
    USBDEV_BULK_NOT_UPDATED = 22
    USBDEV_ADC_OUTPUT_ERROR = 30
    USBDEV_TIME_OVER_ERROR = 101
    USBDEV_TIME_UNDER_ERROR = 102
    USBDEV_TIME_SET_ERROR = 103
    USBDEV_SET_GAIN_ERROR = 106
    USBDEV_SET_TRIGGER_ERROR = 108
    USBDEV_RW_EEP_ADDR_ERROR = 201
    USBDEV_RW_EEP_SIZE_ERROR = 202
    USBDEV_RW_EEP_OVER_ERROR = 203
    USBDEV_RW_EEP_ERROR = 204

class HamamatsuMiniSpectrometer(object):
    def __init__(self,
                 product_id: Union[str, int] = "J4245013",   # J4245013 for SDL2 default
                 calibration_coefficient: List = [1.599374522e2, 3.000949820e-1, 1.964555833e-5, 4.685973475e-10, -1.010224773e-12, 8.932925939e-17]    # default for SDL2
                 ):
        self._load_dll()
        self._func_definitions()
        self.initialize_instrument(product_id=product_id)
        self.read_unit_information()        # get unit info: unit_id, sensor_name, serial_number, wavelength_upper, wavelength_lower
        self.pixel_number                   # retrieve the pixel number based on the unit_id
        self.get_parameter()                # get parameters: integration_time_us, gain, trigger_edge, trigger_mode
        self.get_sensor_data()              # measure a spectrum to "warm up"
        self.wavelength_calibration(calibration_coefficient)

    def _load_dll(self):
        dll_path = Path(__file__).parent.parent/"dll"/"Hamamatsu_DLL"/"spechpk.dll"
        if not dll_path.exists():
            raise FileNotFoundError(f"Spectrometer DLL path {dll_path} does not exist")
        self.lib = WinDLL(str(dll_path))

    def _func_definitions(self):
        # USB_OpenDevice
        self.lib.USB_OpenDevice.argtypes = [c_ushort]  # productID
        self.lib.USB_OpenDevice.restype = c_void_p  # handle or INVALID

        # USB_OpenTargetDevice
        self.lib.USB_OpenTargetDevice.argtypes = [c_char_p]  # unitID
        self.lib.USB_OpenTargetDevice.restype = c_void_p  # handle or INVALID

        # USB_CloseDevice
        self.lib.USB_CloseDevice.argtypes = [c_void_p]  # handle
        self.lib.USB_CloseDevice.restype = None  # None

        # USB_OpenPipe
        self.lib.USB_OpenPipe.argtypes = [c_void_p]  # handle
        self.lib.USB_OpenPipe.restype = c_void_p  # pipe_handle or INVALID

        # USB_ClosePipe
        self.lib.USB_ClosePipe.argtypes = [c_void_p]  # pipe_handle
        self.lib.USB_ClosePipe.restype = None  # None

        # USB_CheckDevice
        self.lib.USB_CheckDevice.argtypes = [c_void_p]  # handle
        self.lib.USB_CheckDevice.restype = c_ushort  # CHECK_NORMAL, CHECK_INVALID, CHECK_REMOVE

        # USB_SetParameter
        self.lib.USB_SetParameter.argtypes = [c_void_p, c_uint, c_byte, c_byte, c_byte]
        # handle
        # integrationTime : us, def 1e5 us = 100 ms
        # gain : def 0x00 Low, 0x01 High, 0xff unavailable
        # triggerEdge : 0x00 rising edge, 0x01 falling edge, 0xff unavailable
        # triggerMode: 0x00 internal, 0x01 edge trigger detection, 0x02 gate trigger mode
        self.lib.USB_SetParameter.restype = c_ushort
        # SUCCESS, INVALID_HANDLE, TIME_OVER_ERROR, TIME_UNDER_ERROR, INVALID_VALUE (gain, triggerEdge, triggerMode), TIME_SET_ERROR, SET_GAIN_ERROR, SET_TRIGGER_ERROR

        # USB_GetParameter
        self.lib.USB_GetParameter.argtypes = [c_void_p, POINTER(c_uint), POINTER(c_byte), POINTER(c_byte),
                                              POINTER(c_byte)]
        # [handle, byref(integrationTime), byref(gain), byref(triggerEdge), byref(triggerMode)]
        self.lib.USB_GetParameter.restype = c_ushort  # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, UNSUCCESS

        # USB_SetEepromDefaultParameter
        self.lib.USB_SetEepromDefaultParameter.argtypes = [c_void_p, c_byte]
        # handle,
        # set : 0: return setting to default when USB connected; 1: recover current setting when USB connected
        self.lib.USB_SetEepromDefaultParameter.restype = c_ushort  # SUCCESS, INVALID_HANDLE, UNSUCCESS

        # USB_ReadUnitInformation
        self.lib.USB_ReadUnitInformation.argtypes = [
            c_void_p,  # handle
            c_byte * 8,  # unitID
            c_byte * 16,  # sensorName
            c_byte * 8,  # serialNumber
            POINTER(c_ushort),  # waveLengthUpper
            POINTER(c_ushort)  # waveLengthLower
        ]
        self.lib.USB_ReadUnitInformation.restype = c_ushort  # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, RW_EEP_ERROR

        # USB_WriteUnitInformation
        self.lib.USB_WriteUnitInformation.argtypes = [
            c_void_p,  # handle
            c_byte * 8,  # unitID
            c_byte * 16,  # sensorName
            c_byte * 8,  # serialNumber
            c_ushort,  # waveLengthUpper
            c_ushort,  # waveLengthLower
            c_byte  # mark = 0xAA, other values prevent writing
        ]
        self.lib.USB_WriteUnitInformation.restype = c_ushort
        # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, INVALID_VALUE, RW_EEP_ERROR

        # USB_ReadCalibrationValue
        self.lib.USB_ReadCalibrationValue.argtypes = [c_void_p, c_double * 6]  # handle, calibration value double * 6
        self.lib.USB_ReadCalibrationValue.restype = c_ushort  # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, RW_EEP_ERROR

        # USB_WriteCalibrationValue
        self.lib.USB_WriteCalibrationValue.argtypes = [c_void_p, c_double * 6, c_byte]
        # handle, calibration value double * 6, mark = 0xAA
        self.lib.USB_WriteCalibrationValue.restype = c_ushort  # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, RW_EEP_ERROR

        # USB_UserReadEEPROM
        self.lib.USB_UserReadEEPROM.argtypes = [c_void_p, c_ushort, c_ushort, c_byte * 256]
        # handle, address 0 to 255, dataLength 1 to 64, buffer
        self.lib.USB_UserReadEEPROM.restype = c_ushort
        # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, RW_EEP_ERROR, RW_EEP_ADDR_ERROR, RW_EEP_SIZE_ERROR, RW_EEP_OVER_ERROR

        # USB_UserWriteEEPROM
        self.lib.USB_UserWriteEEPROM.argtypes = [c_void_p, c_ushort, c_ushort, c_byte * 256]
        # handle, address 0 to 255, dataLength 1 to 64, buffer
        self.lib.USB_UserWriteEEPROM.restype = c_ushort
        # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, RW_EEP_ERROR, RW_EEP_ADDR_ERROR, RW_EEP_SIZE_ERROR, RW_EEP_OVER_ERROR

        # USB_GetSensorData
        self.lib.USB_GetSensorData.argtypes = [c_void_p, c_void_p, c_ushort, c_ushort * 2048]
        # handle, pipe_handle, pixelSize, buffer
        self.lib.USB_GetSensorData.restype = c_ushort
        # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, BULK_NOT_UPDATED, BULK_SIZE_ERROR, BULK_READ_ERROR, ADC_OUTPUT_ERROR

        # USB_GetSensorDataT
        self.lib.USB_GetSensorDataT.argtypes = [c_void_p, c_void_p, c_ushort, c_ushort * 2048, POINTER(c_byte)]
        # handle, pipe_handle, pixelSize, buffer,
        # triggerFlag : 0 for internal trigger operation, 1 for external trigger during integration
        self.lib.USB_GetSensorDataT.restype = c_ushort
        # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, BULK_NOT_UPDATED, BULK_SIZE_ERROR, BULK_READ_ERROR, ADC_OUTPUT_ERROR

        # USB_GetStatusRequestA
        self.lib.USB_GetStatusRequestA.argtypes = [c_void_p, POINTER(c_byte), POINTER(c_ushort)]
        # only available TG_COOLED series
        # handle
        # flag : 0 waiting for cooling to stabilize; 1 cooling is stable
        # count
        self.lib.USB_GetStatusRequestA.restype = c_ushort  # SUCCESS, INVALID_HANDLE, INVALID_PARAMETER, UNSUCCESS

        ###############################################################################
        # Below are not documented in the manual and exact purpose is not 100% clear
        ###############################################################################
        # USB_GetSensorDataA
        self.lib.USB_GetSensorDataA.argtypes = [c_void_p, c_void_p, c_ushort, c_ushort * 2048, POINTER(c_ushort)]
        # handle, pipe_handle, pixelSize, buffer, scanCount
        self.lib.USB_GetSensorDataA.restype = c_ushort  # rtn 0 for success

        # USB_GetSensorDataB
        self.lib.USB_GetSensorDataB.argtypes = [c_void_p, c_void_p, c_ushort, c_ushort * 2048, POINTER(c_ushort),
                                                POINTER(c_byte)]
        # handle, pipe_handle, pixelSize, buffer, scanCount, triggerFlag
        self.lib.USB_GetSensorDataB.restype = c_ushort  # rtn 0 for success

        # USB_GetSensorDataC
        self.lib.USB_GetSensorDataC.argtypes = [c_void_p, c_void_p, c_ushort, c_byte, c_ushort * 2048]
        # handle, pipe_handle, pixelSize, Times, buffer
        self.lib.USB_GetSensorDataC.restype = c_ushort  # rtn 0 for success

        # USB_CheckExternalPower
        self.lib.USB_CheckExternalPower.argtypes = [c_void_p]  # handle
        self.lib.USB_CheckExternalPower.restype = c_ushort  # 0 for success

        # USB_GetTemperature
        self.lib.USB_GetTemperature.argtypes = [c_void_p, POINTER(c_double)]  # handle, temperature
        self.lib.USB_GetTemperature.restype = c_ushort  # 0 for success

        # USB_GetStatusRequestB
        self.lib.USB_GetStatusRequestB.argtypes = [c_void_p, POINTER(c_byte), POINTER(c_ushort)]  # handle, status, data
        self.lib.USB_GetStatusRequestB.restype = c_ushort  # 0 for success

        # USB_ShutDownPeltiter
        self.lib.USB_ShutDownPeltiter.argtypes = [c_void_p, c_byte]  # handle, enable
        self.lib.USB_ShutDownPeltiter.restype = c_ushort

        # USB_GetDllVersion
        self.lib.USB_GetDllVersion.argtypes = [c_byte * 64]  # dllVersion
        self.lib.USB_GetDllVersion.restype = None

        # USB_GetFirmwareInfo
        self.lib.USB_GetFirmwareInfo.argtypes = [c_void_p, c_byte * 256, c_byte * 256]
        # handle, version, buildTime
        self.lib.USB_GetFirmwareInfo.restype = c_ushort  # 0 for success

        # USB_DownloadFirmware
        self.lib.USB_DownloadFirmware.argtypes = [c_void_p, ctypes.c_char_p]  # handle, path
        self.lib.USB_DownloadFirmware.restype = c_ushort  # 0 for success

    def open_device(self, product_id: Union[int, str]) -> None:
        """
        Opens the spectrometer device with the given product ID.

        Args:
            product_id: The product ID of the spectrometer.
            for unknown target device id, use following int:
                0x2900: old
                0x2905: C9404MC, C9405MC, C9406GC
                0x2907: C9913GC, C9914GB
                0x2908: C10082MD, C10083MD
                0x290D: C9404CA, C9404CAH, C9405CC, C9405CB, C9405CA,
                        C11714CA, C11714CB
                0x2909: C10082CA, C10083CA, C10082CAH, C10083CAH,
                        C11713CA

        Raises:
            Exception: If the device cannot be opened.

        Returns:
            None
        """
        if isinstance(product_id, int):
            self.handle = self.lib.USB_OpenDevice(c_ushort(product_id))
        else:
            self.handle = self.lib.USB_OpenTargetDevice(product_id.encode("utf-8"))
        if self.handle == c_void_p(USBDevReturnCode.INVALID_HANDLE_VALUE.value):
            raise Exception("Failed to open device.")
        else:
            print("Device opened successfully.")

    def close_device(self) -> None:
        """
        Closes the spectrometer device.

        Args:
            None

        Returns:
            None
        """
        if self.handle:
            self.lib.USB_CloseDevice(self.handle)
            self.handle = None
            print("Device closed successfully.")
        else:
            print("No device online, nothing to close")

    def open_pipe(self) -> None:
        """
        Opens the communication pipe to the spectrometer.

        Args:
            None

        Raises:
            Exception: If the pipe cannot be opened.

        Returns:
            None
        """
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        self.pipe_handle = self.lib.USB_OpenPipe(self.handle)
        if self.pipe_handle == c_void_p(USBDevReturnCode.INVALID_HANDLE_VALUE.value):
            raise Exception("Failed to open pipe.")
        else:
            print("Pipe opened successfully.")

    def close_pipe(self) -> None:
        """
        Closes the communication pipe to the spectrometer.

        Args:
            None

        Returns:
            None
        """
        if self.pipe_handle:
            self.lib.USB_ClosePipe(self.pipe_handle)
            self.pipe_handle = None
            print("Pipe closed successfully.")

    @property
    def pixel_number(self)->int:
        """
        get the number of pixels of the spectrometer
        :return:
        """
        if self._unit_id[1] == "1":
            self._pixel_number = 256
        elif self._unit_id[1] == "2":
            self._pixel_number = 512
        elif self._unit_id[1] == "3":
            self._pixel_number = 1024
        elif self._unit_id[1] == "4":
            self._pixel_number = 2048
        else:
            raise Exception("Wrong unit id")
        return self._pixel_number

    def set_parameter(
            self,
            integration_time_us: int,
            gain: int = 0,
            trigger_edge: int = 0x00,
            trigger_mode: int = 0x00,
    ) -> None:
        """
        Sets the spectrometer parameters.

        Args:
            integration_time_us: Integration time in microseconds.
            gain: Gain setting (0x00 for Low, 0x01 for High, 0xFF for unavailable).
            trigger_edge: Trigger edge (0x00 for rising edge, 0x01 for falling edge, 0xFF for unavailable).
            trigger_mode: Trigger mode (0x00 for internal, 0x01 for edge trigger, 0x02 for gate trigger).

        Raises:
            Exception: If setting the parameters fails.

        Returns:
            None
        """
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        rtn = self.lib.USB_SetParameter(
            self.handle,
            c_uint(integration_time_us),
            c_byte(gain),
            c_byte(trigger_edge),
            c_byte(trigger_mode),
        )
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to set parameters, error code: {rtn}: {USBDevReturnCode(rtn).name}")
        else:
            print("Parameters set successfully.")

    def get_parameter(self) -> Tuple[int, int, int, int]:
        """
        Retrieves the current spectrometer parameters.

        Args:
            None

        Returns:
            A tuple containing:
                integration_time_us: Integration time in microseconds.
                gain: Gain setting (0x00 for Low, 0x01 for High, 0xFF for unavailable).
                trigger_edge: Trigger edge (0x00 for rising edge, 0x01 for falling edge, 0xFF for unavailable).
                trigger_mode: Trigger mode (0x00 for internal, 0x01 for edge trigger, 0x02 for gate trigger).

        Raises:
            Exception: If getting the parameters fails.
        """
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        integration_time_us = c_uint()
        gain = c_byte()
        trigger_edge = c_byte()
        trigger_mode = c_byte()

        rtn = self.lib.USB_GetParameter(
            self.handle,
            byref(integration_time_us),
            byref(gain),
            byref(trigger_edge),
            byref(trigger_mode),
        )
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to get parameters, error code: {rtn}: {USBDevReturnCode(rtn).name}")
        else:
            # print("Parameters retrieved successfully.")
            self._integration_time_us = integration_time_us.value
            self._gain = gain.value
            self._trigger_edge = trigger_edge.value
            self._trigger_mode = trigger_mode.value
            # return self._integration_time_us, self._gain, self._trigger_edge, self._trigger_mode

    def read_unit_information(self) -> dict:
        """
        Reads the unit information from the spectrometer.

        Args:
            None

        Returns:
            A dictionary containing:
                - unit_id: Unit ID as a string.
                - sensor_name: Sensor name as a string.
                - serial_number: Serial number as a string.
                - wavelength_upper: Upper wavelength limit.
                - wavelength_lower: Lower wavelength limit.

        Raises:
            Exception: If reading the unit information fails.
        """
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        unit_id = (c_byte * 8)()
        sensor_name = (c_byte * 16)()
        serial_number = (c_byte * 8)()
        wavelength_upper = c_ushort()
        wavelength_lower = c_ushort()

        rtn = self.lib.USB_ReadUnitInformation(
            self.handle,
            unit_id,
            sensor_name,
            serial_number,
            byref(wavelength_upper),
            byref(wavelength_lower),
        )
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to read unit information, error code: {rtn}: {USBDevReturnCode(rtn).name}")
        else:
            print("Unit information retrieved successfully.")
            self._unit_id = bytes(unit_id).decode('ascii').rstrip('\x00')
            self._sensor_name = bytes(sensor_name).decode('ascii').rstrip('\x00')
            self._serial_number = bytes(serial_number).decode('ascii').rstrip('\x00')
            self._wavelength_upper = wavelength_upper.value
            self._wavelength_lower = wavelength_lower.value
            return {
                "unit_id": self._unit_id,
                "sensor_name": self._sensor_name,
                "serial_number": self._serial_number,
                "wavelength_upper": self._wavelength_upper,
                "wavelength_lower": self._wavelength_lower,
            }

    def write_unit_information(self,
                               unit_id: str,
                               sensor_name: str,
                               serial_number: str,
                               wavelength_upper: int,
                               wavelength_lower: int
                               ):
        """
        write unit information, use with care
        :param unit_id:
        :param sensor_name:
        :param serial_number:
        :param wavelength_upper:
        :param wavelength_lower:
        :return:
        """
        print("#################################################################\n"
              "##########                                             ##########\n"
              "##########  Are you sure overwrite non volatile mem?   ##########\n"
              "##########  Consider set write_nonvolatile to False.   ##########\n"
              "##########            Type Yes to confirm              ##########\n"
              "##########                                             ##########\n"
              "#################################################################\n"
              )
        if input() != "Yes":
            print("Quit overwite unit information in non volatile mem ")
            return
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        rtn = self.lib.USB_WriteUnitInformation(
            self.handle,
            (c_byte * 8)(*(unit_id.encode('ascii').ljust(8, b'\x00'))),
            (c_byte * 16)(*(sensor_name.encode('ascii').ljust(16, b'\x00'))),
            (c_byte * 8)(*(serial_number.encode('ascii').ljust(8, b'\x00'))),
            c_ushort(wavelength_upper),
            c_ushort(wavelength_lower)
        )
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to write unit information, error code {rtn}: {USBDevReturnCode(rtn).name}.")

    def get_sensor_data(self) -> np.ndarray:
        """
        Retrieves sensor data from the spectrometer.

        Returns:
            A list of sensor data values.

        Raises:
            Exception: If getting the sensor data fails.
        """
        if not self.handle or not self.pipe_handle:
            raise Exception("Device or pipe handle is invalid. Ensure device and pipe are open.")

        buffer = (c_ushort * self._pixel_number)()

        rtn = self.lib.USB_GetSensorData(
            self.handle,
            self.pipe_handle,
            c_ushort(self._pixel_number),
            buffer,
        )
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to get sensor data, error code: {rtn}: {USBDevReturnCode(rtn).name}")
        else:
            print("Sensor data retrieved successfully.")
            return np.array(buffer)

    def get_dll_version(self) -> str:
        """
        Retrieves the DLL version information.

        Args:
            None

        Returns:
            The DLL version as a string.

        Raises:
            Exception: If retrieving the DLL version fails.
        """
        version_buffer = (c_byte * 16)()
        self.lib.USB_GetDllVersion(version_buffer)
        version_str = bytes(version_buffer).decode('ascii').rstrip('\x00')
        if not version_str:
            raise Exception("Failed to retrieve DLL version.")
        else:
            print(f"DLL Version: {version_str}")
            return version_str

    def get_firmware_info(self) -> dict:
        """
        Retrieves the firmware version and build time from the spectrometer.

        Args:
            None

        Returns:
            A dictionary containing:
                - firmware_version: Firmware version as a string.
                - build_time: Build time as a string.

        Raises:
            Exception: If retrieving the firmware information fails.
        """
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        version_buffer = (c_byte * 16)()
        build_time_buffer = (c_byte * 16)()

        rtn = self.lib.USB_GetFirmwareInfo(
            self.handle,
            version_buffer,
            build_time_buffer,
        )
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to get firmware info, error code: {rtn}: {USBDevReturnCode(rtn).name}")
        else:
            firmware_version = bytes(version_buffer).decode('ascii').rstrip('\x00')
            build_time = bytes(build_time_buffer).decode('ascii').rstrip('\x00')
            print("Firmware information retrieved successfully.")
            return {
                "firmware_version": firmware_version,
                "build_time": build_time,
            }

    def check_device(self) -> int:
        """
        Checks the status of the device.

        Args:
            None

        Returns:
            A status code indicating the device status.
            11: normal
            12: invalid
            13: removed

        Raises:
            Exception: If the device handle is invalid.
        """
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        rtn = self.lib.USB_CheckDevice(self.handle)
        print(f"Device status code: {rtn}: {USBDevReturnCode(rtn).name}")
        return rtn

    def read_calibration_values(self) -> np.ndarray:
        """
        Reads the calibration values from the spectrometer.

        Args:
            None

        Returns:
            An array of six calibration values.

        Raises:
            Exception: If reading the calibration values fails.
        """
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        calibration_values = (c_double * 6)()

        rtn = self.lib.USB_ReadCalibrationValue(
            self.handle,
            calibration_values,
        )
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to read calibration values, error code: {rtn}: {USBDevReturnCode(rtn).name}")
        else:
            return np.array(calibration_values)

    def write_calibration_values(self, a0, a1, a2, a3, a4, a5):
        """
        write the calibration values, 6 floats
        :param a0:
        :param a1:
        :param a2:
        :param a3:
        :param a4:
        :param a5:
        :return:
        """
        print("#################################################################\n"
              "##########                                             ##########\n"
              "########## Are you sure overwrite non calibration val? ##########\n"
              "##########  Consider set write_nonvolatile to False.   ##########\n"
              "##########            Type Yes to confirm              ##########\n"
              "##########                                             ##########\n"
              "#################################################################\n"
              )
        if input() != "Yes":
            print("Quit overwite calibration values")
            return
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        rtn = self.lib.USB_WriteCalibrationValue(self.handle,
                                                 (c_double * 6)(a0, a1, a2, a3, a4, a5),
                                                 c_byte(0xAA)
                                                 )
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to write calibration values, error code: {rtn}: {USBDevReturnCode(rtn).name}")

    def read_user_eeprom(self, address: int, length: int)->str:
        """
        Read user area of eeprom
        :param address: address to start with, 0-255
        :param length: length to read
        :return:
        """
        if address < 0 or address > 0xff:
            raise ValueError("Address out of range 0x00 - 0xff")
        if length <= 0 or length > 0x40:
            raise ValueError("Length out of range 0x01 - 0x40")
        if address + length > 0xff:
            raise ValueError("Read area out of range 0xff")
        buffer = (c_byte * length)()
        rtn = self.lib.USB_UserReadEEPROM(self.handle, c_ushort(address), c_ushort(length), buffer)
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to read EEPROM, error code: {rtn}: {USBDevReturnCode(rtn).name}")
        return bytes(buffer).decode()

    def write_user_eeprom(self, address: int, length: int):
        """
        Write user area of eeprom
        :param address: address to start with, 0-255
        :param length: length to read
        :return:
        """
        if address < 0 or address > 0xff:
            raise ValueError("Address out of range 0x00 - 0xff")
        if length <= 0 or length > 0x40:
            raise ValueError("Length out of range 0x01 - 0x40")
        if address + length > 0xff:
            raise ValueError("Read area out of range 0xff")
        buffer = (c_byte * length)()
        rtn = self.lib.USB_UserWriteEEPROM(self.handle, c_ushort(address), c_ushort(length), buffer)
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to write EEPROM, error code: {rtn}: {USBDevReturnCode(rtn).name}")
        return bytes(buffer).decode()

    def set_eeprom_default_parameter(self, set_default: bool) -> None:
        """
        Sets the EEPROM default parameter behavior.

        Args:
            set_default: If True, returns to default settings when USB is connected.
                         If False, recovers current settings when USB is connected.

        Raises:
            Exception: If setting the EEPROM default parameter fails.

        Returns:
            None
        """
        if not self.handle:
            raise Exception("Device handle is invalid. Open the device first.")
        set_value = c_byte(0x00 if set_default else 0x01)
        rtn = self.lib.USB_SetEepromDefaultParameter(self.handle, set_value)
        if rtn != USBDevReturnCode.USBDEV_SUCCESS.value:
            raise Exception(f"Failed to set EEPROM default parameter, error code: {rtn}")
        else:
            print("EEPROM default parameter set successfully.")

    def initialize_instrument(self, product_id: Union[int, str]):
        """
        initialize an instrument by creating the handle and pipe_handle
        :param device_id:
        :return:
        """
        self.open_device(product_id=product_id)
        self.open_pipe()

    def close_instrument(self):
        """
        close the pipe and device communication
        :return:
        """
        self.close_pipe()
        self.close_device()

    def wavelength_calibration(self, calibration_coefficient: Union[np.ndarray, List, Tuple]) -> None:
        """
        Create the wavelength calibration
        :param calibration_coefficient: calibration coefficient given by factory
        :return: calibrated wavelength
        """
        pix = np.arange(1, self._pixel_number+1)
        self._wavelength = np.polyval(calibration_coefficient[::-1], pix)

    @property
    def wavelength(self)->np.ndarray:
        """
        Get the calibrated wavelength
        :return: calibrated wavelength
        """
        return self._wavelength

    @property
    def trigger_edge(self) -> int:
        """
        get the trigger edge
        :return: 0x00 for rising, 0x01 for falling, 0x02 for not available
        """
        rtn = self.get_parameter()
        return self._trigger_edge

    @trigger_edge.setter
    def trigger_edge(self, trigger_edge: int):
        """
        set trigger edge
        :param trigger_edge: 0x00 for rising, 0x01 for falling, 0x02 for not available
        :return:
        """
        if trigger_edge not in (0x00, 0x01, 0x02):
            raise ValueError("Trigger edge must be 0x00, 0x01 or 0x02")
        self.set_parameter(integration_time_us=self._integration_time_us,
                           gain=self._gain,
                           trigger_edge=trigger_edge,
                           trigger_mode=self._trigger_mode
                           )
        self._trigger_edge = trigger_edge

    @property
    def trigger_mode(self) -> int:
        """
        get the trigger mode
        :return: 0x00 for internal, 0x01 for edge trigger, 0x02 for gate trigger
        """
        rtn = self.get_parameter()
        return self._trigger_mode

    @trigger_mode.setter
    def trigger_mode(self, trigger_mode: int):
        """
        set the trigger mode
        :param trigger_mode: 0x00 for internal, 0x01 for edge trigger, 0x02 for gate trigger
        :return:
        """
        if trigger_mode not in (0x00, 0x01, 0x02):
            raise ValueError("Trigger mode must be 0x01, 0x02, 0x03")
        self.set_parameter(integration_time_us=self._integration_time_us,
                           gain=self._gain,
                           trigger_edge=self._trigger_edge,
                           trigger_mode=trigger_mode
                           )
        self._trigger_mode = trigger_mode

    @property
    def gain(self)->int:
        """
        get the gain
        :return: 0x00 for low gain, 0x01 for high gain, 0xff for not available
        """
        rtn = self.get_parameter()
        return self._gain

    @gain.setter
    def gain(self, gain: int):
        if gain not in (0x00, 0x01, 0xff):
            raise ValueError("Gain must be 0x00, 0x01, 0xff")
        self.set_parameter(integration_time_us=self._integration_time_us,
                           gain=gain,
                           trigger_edge=self._trigger_edge,
                           trigger_mode=self._trigger_mode
                           )
        self._gain = gain

    @property
    def integration_time(self) -> float:
        """
        get the integration time in second
        :return:
        """
        return self._integration_time_us * 1e-6

    @property
    def integration_time_us(self) -> int:
        """
        get the integration time in microsecond
        :return:
        """
        rtn = self.get_parameter()
        return self._integration_time_us

    @integration_time_us.setter
    def integration_time_us(self, integration_time_us: int):
        """
        set the integration time
        :param integration_time_us:
        :return:
        """
        if integration_time_us < 10000 or integration_time_us > 10000000:
            raise ValueError("Integration time out of range. 1e4-1e7 us/10-10000 ms/0.01-10 s.")
        self.set_parameter(integration_time_us=integration_time_us,
                           gain=self._gain,
                           trigger_edge=self._trigger_edge,
                           trigger_mode=self._trigger_mode
                           )
        time.sleep(0.5 + 1.2*integration_time_us/1e6)
        self._integration_time_us = integration_time_us

    @integration_time.setter
    def integration_time(self, integration_time: float):
        """
        set the integration time in seconds
        :param integration_time:
        :return:
        """
        self.integration_time_us = int(integration_time * 1e6)

    def measure_spectrum(self, integration_time: float)->np.ndarray:
        """
        measure the spectrum
        Hamamatsu spectrometer is continuously measuring and return the reading from last duration of integration time
            therefore need time.sleep to ensure the measurement is from the start of calling of this function
            average reading time elapse is 4 ms
        In case of integration time > 10 s, use ceil to slice rounds and sum up
        :param integration_time:
        :return:
        """
        # self.integration_time = integration_time
        if self.check_device() != 11:
            raise Exception("Device abnormal")
        rtn = np.zeros(2048, dtype=np.uint32)
        measurement_rounds = ceil(integration_time / 10)
        integration_time_per_round = integration_time / measurement_rounds
        # if integration_time_per_round != self._integration_time:
        # self.integration_time = integration_time_per_round
        for i in range(0, measurement_rounds):
            # time.sleep(integration_time_per_round + 0)
            self.integration_time = integration_time_per_round
            rtn += self.get_sensor_data()
        return rtn

    def auto_scale(self, lower: int = 1024, upper: int = 61439):
        """
        automatically adjust
        :param lower:
        :param upper:
        :return:
        """
        int_time = 0.01
        scale_factor = 2
        while True:
            rtn = max(self.measure_spectrum(int_time))
            if rtn > upper:
                raise Exception("Too strong light!")
            elif rtn < lower:
                int_time *= scale_factor
                if int_time > 30:
                    raise Exception("Too weak light!")
            else:
                return int_time
