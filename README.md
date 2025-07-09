# Auto_Polymerization

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains the **Auto_Polymerization platform** for automated polymer synthesis and characterization.

## 🚀 Quick Start

### Device Testing

For testing real devices in your Auto_Polymerization platform, see the demo folder:

```bash
cd Auto_Polymerization/demo
python demo_device_test.py
```

This will guide you through testing individual devices with safe parameters.

For comprehensive device testing:

```bash
cd Auto_Polymerization/demo
python device_test_controller.py
```

📖 See [`Auto_Polymerization/demo/DEVICE_TESTING_README.md`](Auto_Polymerization/demo/DEVICE_TESTING_README.md) for detailed documentation.

## 📦 Required Packages and Setup

### 🔧 Hardware Drivers

Install drivers for the devices used in this project:

- **[Thorlabs CCS200 Spectrometer](https://www.thorlabs.com/thorproduct.cfm?partnumber=CCS200#ad-image-0)** - UV-VIS spectroscopy
- **[Thorlabs upLED Controller](https://www.thorlabs.com/thorproduct.cfm?partnumber=UPLED)** - LED control

### 🐍 Python Environment

**Python Version:** 3.10

Install the linear actuator and valves control package from the local source in editable mode:

```bash
pip install -e src/linear_actuator_and_valves/
```

### 📚 Core Dependencies

```bash
pip install scipy numpy pandas matplotlib pyserial nmrglue requests pyyaml medusa-sdl
```

### 🔬 MatterLab Packages

Install from [MatterLab devices repository](https://gitlab.com/aspuru-guzik-group/self-driving-lab/devices):

#### Easy Installation (if available):
```bash
pip install matterlab_hotplates
pip install matterlab_pumps
pip install matterlab_serial_device
```

#### Manual Installation:

**Hotplates, Pumps, Serial Device:**

https://gitlab.com/aspuru-guzik-group/self-driving-lab/devices



**Spectrometers:**

- **NMR (Nanalysis Benchtop):**

  git clone https://gitlab.com/aspuru-guzik-group/self-driving-lab/devices/nmr
  cd nmr
  git checkout develop
  pip install -e .


- **UV-VIS (Thorlabs CCS200):**

  git clone https://gitlab.com/aspuru-guzik-group/self-driving-lab/devices/spectrometer
  cd spectrometer
  git checkout develop
  pip install -e .


> **Note:** If access is not public, contact Han Hao at University of Toronto.

### ⚙️ Configuration

**CSS200 Spectrometer DLL:**
Potentially you need to update the `DLL_FILE` value in `ccs_spectrometer.py` in the matterlab package:
The correct file path is typically: 
DLL_FILE = Path(r"C:\Program Files\IVI Foundation\VISA\Win64\Bin\TLCCS_64.dll")
#

**Arduino Setup:**
1. Install Arduino IDE on your PC
2. Upload the Arduino code from `users/setup/` to your Arduino board
3. An overview of the hardware connections of the GPIO pins is given in "Arduino_contacts_overview_2025_06_27_bb.jpg"
## ⚠️ Important Notes



## 📁 Project Structure

```
Auto_Polymerization/
├── 📂 demo/                          # Device testing and demo scripts
│   ├── 🔧 device_test_controller.py  # Main testing framework
│   ├── 🎯 demo_device_test.py        # User-friendly demo script
│   ├── 📖 DEVICE_TESTING_README.md   # Device testing documentation
│   └── 🔬 test_uv_vis_utils.py       # UV-VIS testing utilities
├── 📂 src/                           # Source code modules
│   ├── 🔬 UV_VIS/                    # UV-VIS spectroscopy utilities
│   ├── 💧 liquid_transfers/          # Liquid transfer modules
│   └── ⚙️ linear_actuator_and_valves/ # Hardware control modules
├── 📂 workflow_steps/                # Workflow step modules
├── 📂 users/                         # User configuration and data
│   ├── ⚙️ config/                    # Configuration files
│   ├── 📊 data/                      # Data storage
│   └── 🔧 setup/                     # Setup files
├── 📂 Data/                          # Experimental data
└── 🎮 platform_controller.py         # Main workflow controller
```

## 🧩 Main Components

| Component | Description | Location |
|-----------|-------------|----------|
| **🎮 Platform Controller** | Main workflow orchestration | `platform_controller.py` |
| **🔧 Device Testing** | Comprehensive device testing framework | `demo/` |
| **🔬 UV-VIS Utilities** | Spectroscopy data acquisition and analysis | `src/UV_VIS/` |
| **⚙️ Workflow Modules** | Individual workflow steps | `workflow_steps/` |

## 🚀 Getting Started

1. **📦 Install dependencies** from as described above
2. **⚙️ Configure your hardware** using the setup files in `users/setup/`
3. **🔧 Test your devices** using the demo scripts in `demo/`
4. **🧪 Run experiments** using `platform_controller.py`

## 📚 Documentation

| Topic | Location |
|-------|----------|
| **🔧 Device Testing** | [`Auto_Polymerization/demo/DEVICE_TESTING_README.md`](Auto_Polymerization/demo/DEVICE_TESTING_README.md) |
| **🔬 UV-VIS Utilities** | [`Auto_Polymerization/src/UV_VIS/uv_vis_utils.py`](Auto_Polymerization/src/UV_VIS/uv_vis_utils.py) |
| **⚙️ Workflow Steps** | Individual modules in `workflow_steps/` |

## 🔧 Development

If you want to develop the package further, use the development mode:

```bash
pip install -e .
```

Changes to the source code will be picked up immediately.

## 📄 License

[MIT License](LICENSE.txt) - see the [LICENSE.txt](LICENSE.txt) file for details.

## 🆘 Support

For issues and questions:

1. **🔧 Check the device testing documentation** in `Auto_Polymerization/demo/`
2. **📖 Review the troubleshooting sections** in the README files
3. **🔌 Verify hardware connections** and configuration
4. **🐛 Open an issue** on GitHub or contact the maintainers

---

**❓ Questions or issues?**  
Please [open an issue](https://github.com/your-repo/issues) on GitHub or contact the maintainers.
