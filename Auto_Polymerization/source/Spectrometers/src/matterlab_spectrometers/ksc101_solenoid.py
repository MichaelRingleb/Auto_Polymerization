from pathlib import Path
from ctypes import create_string_buffer, cdll, c_char_p


DLL_FILE = Path.cwd().parent.parent/"dll"/"Kinesis"/"Thorlabs.MotionControl.KCube.Solenoid.dll"

class KSC101:
    def __init__(self):
        self._load_dll()
        self._build_device_list()
        self._get_device_list_size()
        self._get_device_list()

    def _load_dll(self):
        """
        load the dll
        :return:
        """
        print(DLL_FILE)
        assert DLL_FILE.exists(), "Spectrometer DLL path is wrong, check!"
        self.lib = cdll.LoadLibrary(str(DLL_FILE))
        # self.lib = cdll.LoadLibrary(str(Path(r"C:\Users\han\Aspuru-Guzik Lab Dropbox\Hao Han\PythonScript\Han\Spectrometer\Spectrometer\dll\Kinesis\Thorlabs.MotionControl.KCube.Solenoid.dll")))

    def _build_device_list(self):
        """
        build device list
        need to be called at beginning of initialization
        :return:
        """
        self.lib.TLI_BuildDeviceList()

    def _get_device_list_size(self):
        """
        get device list size
        call after build dev list, before get dev list
        :return:
        """
        self.lib.TLI_GetDeviceListSize()

    def _get_device_list(self):
        """
        get device list
        :return:
        """
        data = create_string_buffer(0xff)
        self.lib.TLI_GetDeviceListByTypeExt(data, 0xff, 68)
        self.device_list = data.value.decode("utf-8").split(",")[:-1]

    def open_communication(self, dev_ord =0):
        """
        open communication with device
        :return:
        """
        ser = c_char_p(self.device_list[dev_ord].encode())
        self.lib.SC_Open(ser)

    def close_communication(self, dev_ord = 0):
        ser = c_char_p(self.device_list[dev_ord].encode())
        self.lib.SC_Close(ser)

    def open(self, dev_ord = 0):
        ser = c_char_p(self.device_list[dev_ord].encode())
        self.lib.SC_SetOperatingState(ser, 0x01)

    def close(self, dev_ord = 0):
        ser = c_char_p(self.device_list[dev_ord].encode())
        self.lib.SC_SetOperatingState(ser, 0x02)