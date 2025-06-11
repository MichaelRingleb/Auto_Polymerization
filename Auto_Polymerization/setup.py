from setuptools import setup, find_packages

setup(
    name="Auto_Polymerization",
    version="0.1",
   packages=find_packages(where="source/Pumps/src") + find_packages(where="source/SerialDevice/src"),
    package_dir={
        "matterlab_pumps": "source/Pumps/src/matterlab_pumps",
        "matterlab_serial_device": "source/SerialDevice/src/matterlab_serial_device"
    },
)