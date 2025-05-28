from setuptools import setup, find_packages

setup(
    name='Stirrer',
    version='0.1',
    packages=find_packages(),
    install_requires=["pyserial", "datetime" ],  # Hier ggf. Abhängigkeiten eintragen
)