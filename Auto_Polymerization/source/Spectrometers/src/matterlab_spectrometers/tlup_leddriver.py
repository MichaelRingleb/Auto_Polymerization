from ctypes import CDLL, c_byte, c_bool, c_void_p, c_double, c_int, c_uint, byref, c_long, c_short, c_ushort
from pathlib import Path
import time


class TLUPLedDriverError(Exception):
    pass


class TLUPLedDriver():
    def __init__(self, com_port: str):
        self._update_serial_port_visa_format(com_port = com_port)
        self._load_dll()
        self.handle = c_long(-1)
        self._find_device()
        self.initialize()
        self.get_dev_info()
        self.get_led_info()
        self.current_startup = self.current_min
        self.on_startup = False
        pass

    def _load_dll(self):
        dll_path = Path(__file__).parent.parent / "dll" / "TLUP_DLL" / "TLUP_64.dll"
        if not dll_path.exists():
            raise FileNotFoundError(f"LED driver DLL path {dll_path} does not exist")
        self.lib = CDLL(str(dll_path))

    def check_handle(func):
        """
        Decorator to check if the handle is valid
        :return:
        """
        def wrapper(self, *args, **kwargs):
            if not self.handle or self.handle.value < 0:
                raise TLUPLedDriverError("Instrument handle not valid.")
            return func(self, *args, **kwargs)
        return wrapper

    def _update_serial_port_visa_format(self, com_port: str):
        """
        update serial port determination, homogenize linux and windows settings
        :param com_port:
        :return:
        """
        if com_port[0:3] == "COM":
            # COM{x} etc. for Windows => ASRL1{x}::INSTR
            self._com_port = f"ASRL{com_port[3:]}::INSTR"
        elif com_port[0:9] == "/dev/ttyS":
            # /dev/ttyS{x} for Linux Serial direct => ASRL{x+1}::INSTR
            self._com_port = f"ASRL{int(com_port[9:])+1}::INSTR"
        else:
            # /dev/ttyUSB{x}, /dev/ttyACM{x} for Linux USB Serial => ASRL/dev/ttyUSB{x}::INSTR
            self._com_port = f"ASRL{com_port}::INSTR"

    @check_handle
    def get_error_query(self, error_number: int) -> str:
        """
        get the error message based on error number
        :param error_number:
        :return:
        """
        # if self.handle <= 0:
        #     raise ValueError("Negative handle, no dev connected.")
        err_msg = (c_byte * 256)()
        rtn = self.lib.TLUP_errorQuery(self.handle, c_int(error_number), err_msg)
        if rtn == 0:
            return bytes(err_msg).decode()
        else:
            raise ValueError("Unknown Status")

    def _find_device(self) -> int:
        """
        find connected devices
        :return: The number connected devices that are supported by this driver
        """
        num_dev = c_uint(0)
        rtn = self.lib.TLUP_findRsrc(0, byref(num_dev))
        if rtn != 0:
            raise SystemError("Find resource error")
        if num_dev.value == 0:
            raise ValueError("No UPLED detected.")
        # self._num_dev = num_dev.value
        for i in range(0, num_dev.value):
            if self.get_device_name(i) == self._com_port:
                self.dev_num = i
                return
        raise TLUPLedDriverError("No device connected with expected COM/Serial port")

    def get_device_name(self, dev_num: int) -> str:
        """
        get the name by device number, count from 0
        :param dev_num:
        :return:
        """
        name = (c_byte * 256)()
        rtn = self.lib.TLUP_getRsrcName(0, c_uint(dev_num), name)
        if rtn != 0:
            raise SystemError(
                f"Get resource name failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        dev_name = bytes(name).decode().rstrip("\x00")
        return dev_name

        # self.devs[str(dev_num)]["name"] = dev_name
        # print(f"Device No. {dev_num} name {dev_name}")

    def initialize(self):
        """
        Initialize the instrument and get the instrument handle
        :return:
        """
        id_query = c_bool(0)
        reset_device = c_bool(0)
        rtn = self.lib.TLUP_init(self._com_port.encode("ascii"), id_query, reset_device, byref(self.handle))
        if rtn != 0:
            raise TLUPLedDriverError("Initialize failed, can not create instrument handle.")

    def reset(self):
        """
        reset the device
        :return:
        """
        rtn = self.lib.TLUP_reset(self.handle)
        if rtn != 0:
            raise TLUPLedDriverError("Reset failed.")

    def close(self):
        """
        Disconnect the device
        :return:
        """
        rtn = self.lib.TLUP_close(self.handle)
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Close device failed, error code {rtn}, error message {self.get_error_query(rtn)}")

    @check_handle
    def get_dev_info(self) -> None:
        """
        get the device info
        :return:
        """
        model = (c_byte * 256)()
        serial = (c_byte * 256)()
        manufacture = (c_byte * 256)()
        avaibility = c_bool()

        rtn = self.lib.TLUP_getRsrcInfo(self.handle, c_uint(self.dev_num), model, serial, manufacture, byref(avaibility))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get resource info failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        self._dev_model = bytes(model).decode().rstrip("\x00")
        self._dev_serial_num = bytes(serial).decode().rstrip("\x00")
        self._dev_manufacture = bytes(manufacture).decode().rstrip("\x00")
        self._dev_avaibility = bool(avaibility)


    @check_handle
    def get_led_info(self) -> None:
        """
        get the led info
        :return:
        """
        name = (c_byte * 256)()
        serial = (c_byte * 256)()
        current_limit = c_double(0)
        forward_voltage = c_double(0)
        wavelength = c_double(0)
        rtn = self.lib.TLUP_getLedInfo(self.handle, name, serial,
                                       byref(current_limit), byref(forward_voltage), byref(wavelength))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get Led info failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        self._led_name = bytes(name).decode().rstrip("\x00")
        self._led_serial_num = bytes(serial).decode().rstrip("\x00")
        self._current_max = current_limit.value
        self._current_max_hardware = current_limit.value
        self._forward_voltage = forward_voltage.value
        self._wavelength = wavelength.value

    @property
    def current_limit_max(self)->float:
        """
        get the current limit of the led
        :return:
        """
        return self._current_max_hardware

    @property
    def forward_voltage(self)->float:
        """
        get the forward voltage of the led
        :return:
        """
        return self._forward_voltage

    @property
    def wavelength(self)-> float:
        """
        get the wavelength of the led
        :return:
        """
        return self._wavelength

    @check_handle
    def get_led_operation_mode(self)->int:
        """
        get the led operation mode, print description
        :return: operation code as int
        """
        flag = c_uint()
        description = (c_byte*256)()
        rtn = self.lib.TLUP_getOpMode(self.handle, byref(flag), description)
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get Led operation mode failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        print(f"LED operation mode code {flag.value}")
        print(bytes(description).decode().rstrip("\x00"))
        self._led_operation_mode = flag.value
        return flag.value

    @property
    @check_handle
    def temperature_unit(self)->str:
        """
        Get the temperature unit, K, C, or F
        :return:
        """
        tu = c_byte()
        rtn = self.lib.TLUP_getTempUnit(self.handle, byref(tu))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get temperature unit failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        if tu.value == 0:
            self._temp_unit = "K"
            return self._temp_unit
        elif tu.value == 1:
            self._temp_unit = "C"
            return self._temp_unit
        else:
            self._temp_unit = "F"
            return self._temp_unit

    @temperature_unit.setter
    @check_handle
    def temperature_unit(self, unit: str):
        """
        Set the temperature unit
        :param unit: K, C, or F
        :return:
        """
        if unit == "K":
            unit_num = 0
        elif unit == "C":
            unit_num = 1
        elif unit == "F":
            unit_num = 2
        else:
            raise ValueError("Invalid Temp unit, must be K, C, F")
        rtn = self.lib.TLUP_setTempUnit(self.handle, c_ushort(unit_num))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Set temperature unit failed, error code {rtn}, error message {self.get_error_query(rtn)}")

    @property
    @check_handle
    def device_temp(self)->float:
        """
        Get current device temperature
        :return:
        """
        temp = c_double()
        rtn = self.lib.TLUP_measDeviceTemperature(self.handle, byref(temp))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get device temperature failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        self._device_temperature = temp.value
        return self._device_temperature

    @property
    @check_handle
    def current(self)->float:
        """
        Measure the led current
        :return:
        """
        current = c_double()
        rtn = self.lib.TLUP_measureLedCurrent(self.handle, byref(current))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get LED current failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        return current.value

    @current.setter
    @check_handle
    def current(self, current: float):
        """
        set the LED current
        :param current:
        :return:
        """
        if current > self._current_max:
            raise ValueError(f"Current setting > max {self._current_max} A.")
        elif current < self._current_min:
            raise ValueError(f"Current setting < min {self._current_min} A.")
        rtn = self.lib.TLUP_setLedCurrentSetpoint(self.handle, c_double(current))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Set LED current failed, error code {rtn}, error message {self.get_error_query(rtn)}")

    @property
    @check_handle
    def current_max(self)->float:
        """
        Get the current limit of the LED
        :return:
        """
        limit = c_double(0)
        rtn = self.lib.TLUP_getLedCurrentLimitUser(self.handle, c_short(0), byref(limit))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get LED current max failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        self._current_max = limit.value
        return self._current_max

    @property
    @check_handle
    def current_min(self):
        """
        Get the current min of the LED
        :return:
        """
        limit = c_double(0)
        rtn = self.lib.TLUP_getLedCurrentLimitUser(self.handle, c_short(1), byref(limit))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get LED current min failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        self._current_min = limit.value
        return self._current_min

    @current_max.setter
    @check_handle
    def current_max(self, limit:float):
        """
        Set the
        :param limit:
        :return:
        """
        if limit > self._current_max_hardware:
            raise TLUPLedDriverError(f"Current limit exceed hardware upper boundary {self._current_max_hardware} A.")
        rtn = self.lib.TLUP_setLedCurrentLimitUser(self.handle, c_double(limit))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Set LED current max failed, error code {rtn}, error message {self.get_error_query(rtn)}")

    @property
    @check_handle
    def on(self)-> bool:
        """
        Get if the LED is ON or OFF
        :return:
        """
        state = c_bool()
        rtn = self.lib.TLUP_getLedOutputState(self.handle, byref(state))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get LED ON/OFF state failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        self._on = state.value
        return self._on

    @on.setter
    @check_handle
    def on(self, state: bool = False):
        """
        Set the state of LED ON/OFF
        :param state:
        :return:
        """
        rtn = self.lib.TLUP_switchLedOutput(self.handle, c_bool(state))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Set LED ON/OFF failed, error code {rtn}, error message {self.get_error_query(rtn)}")

    @property
    @check_handle
    def current_startup(self)->float:
        """
        Get the start up current of LED
        :return:
        """
        current = c_double()
        rtn = self.lib.TLUP_getLedCurrentSetpointStartup(self.handle, c_short(0), byref(current))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get LED start up current failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        return current.value

    @current_startup.setter
    @check_handle
    def current_startup(self, current: float):
        """
        Set the current on start up
        :param current:
        :return:
        """
        if current > self._current_max:
            raise  ValueError(f"Start up current exceed limit {self._current_max} A.")
        rtn = self.lib.TLUP_setLedCurrentSetpointStartup(self.handle, c_double(current))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Set LED start up current failed, error code {rtn}, error message {self.get_error_query(rtn)}")

    @property
    @check_handle
    def on_startup(self)->bool:
        """
        Get if the LED set to on up on start up
        :return:
        """
        state = c_bool()
        rtn = self.lib.TLUP_getLedSwitchOnAtStartup(self.handle, byref(state))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get LED start up state failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        return state.value

    @on_startup.setter
    @check_handle
    def on_startup(self, state: bool):
        """
        Set the LED ON/OFF when start up
        :param state:
        :return:
        """
        rtn = self.lib.TLUP_setLedSwitchOnAtStartup(self.handle, c_bool(state))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Set LED start up state failed, error code {rtn}, error message {self.get_error_query(rtn)}")

    @property
    @check_handle
    def on_disconnect(self)->bool:
        """
        Get if the LED keeps on after disconnect
        :return:
        """
        state = c_bool()
        rtn = self.lib.TLUP_getLedSwitchOffAtDisconnect(self.handle, byref(state))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get LED disconnect state failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        return not state.value

    @on_disconnect.setter
    @check_handle
    def on_disconnect(self, state: bool):
        """
        Set the LED stay ON/OFF after disconnect
        :param state:
        :return:
        """
        rtn = self.lib.TLUP_setLedSwitchOffAtDisconnect(self.handle, c_bool(not state))
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Set LED disconnect state failed, error code {rtn}, error message {self.get_error_query(rtn)}")

    @property
    @check_handle
    def build_date(self)->str:
        """
        Get the build date and time
        :return:
        """
        build_datetime = (c_byte*256)()
        rtn = self.lib.TLUP_getBuildDateAndTime(self.handle, build_datetime)
        if rtn != 0:
            raise TLUPLedDriverError(
                f"Get LED disconnect state failed, error code {rtn}, error message {self.get_error_query(rtn)}")
        return bytes(build_datetime).decode().rstrip("\x00")

    @check_handle
    def save_current_mode_to_NVMEM(self):
        """
        Save LED current settings to NMVE
        :return:
        """
        print(
            "#############################################################"
            "####  Becareful write to NVMEM, type Yes to continue...  ####"
            "#############################################################"
        )
        if input() == "Yes":
            self.current_max
            self.current_min
            self.lib.TLUP_saveToNVMEM(self.handle, c_short(2))
        else:
            print("Quit save to NVMEM.")


# up = TLUPLedDriver("COM17")
# up.current = 0.1
# up.on = True
# print(up.current)
# print(up.on)
# time.sleep(5)
# print(up.current_max)
# up.current = 1.0
# time.sleep(1)
# up.on = False

"""
from ctypes import CDLL, c_byte, c_bool, c_void_p, c_double, c_int, c_uint, byref, create_string_buffer
from pathlib import Path
lib = CDLL(str(Path.cwd()/"src"/"dll"/"TLUP_DLL"/"TLUP_64.dll"))
dev_count = c_uint(0)
lib.TLUP_findRsrc(0, byref(dev_count))
handle = c_void_p()
lib.TLUP_init(b"ASRL17::INSTR", 0, 0, byref(handle))
"""