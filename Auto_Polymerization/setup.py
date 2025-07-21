"""
Auto_Polymerization Package Setup

This setup.py file configures the Auto_Polymerization package for installation and distribution.
It includes package discovery, dependencies, and metadata for the complete automated
polymerization platform.

The Auto_Polymerization platform provides:
- Automated polymer synthesis workflows
- NMR and UV-VIS spectroscopy integration
- Error-safe liquid handling with COM port conflict resolution
- Comprehensive data analysis and monitoring
- Modular workflow design for easy customization

Dependencies:
- medusa-sdl: Hardware control framework
- matterlab packages: Spectroscopy and device control
- numpy, scipy: Numerical computing
- matplotlib: Plotting and visualization
- pybaselines: Baseline correction for NMR
- lmfit: Curve fitting and analysis

Author: Michael Ringleb (with help from cursor.ai)
Date: [Current Date]
Version: 1.0
"""

from setuptools import setup, find_packages

setup(
    name="Auto_Polymerization",
    version="1.0",
    description="Automated Polymer Synthesis and Characterization Platform",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Michael Ringleb",
    author_email="michael.ringleb@example.com",
    url="https://github.com/your-repo/Auto_Polymerization",
    packages=find_packages(where="src") + find_packages(where="source/Pumps/src") + find_packages(where="source/SerialDevice/src"),
    package_dir={
        "matterlab_pumps": "source/Pumps/src/matterlab_pumps",
        "matterlab_serial_device": "source/SerialDevice/src/matterlab_serial_device"
    },
    install_requires=[
        "numpy>=1.20.0",
        "scipy>=1.7.0",
        "matplotlib>=3.3.0",
        "pandas>=1.3.0",
        "pyserial>=3.5",
        "pyyaml>=5.4",
        "requests>=2.25.0",
        "pybaselines>=0.2.0",
        "lmfit>=1.0.0",
        "medusa-sdl>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=0.5.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    keywords="polymerization, automation, NMR, UV-VIS, spectroscopy, chemistry",
    project_urls={
        "Bug Reports": "https://github.com/your-repo/Auto_Polymerization/issues",
        "Source": "https://github.com/your-repo/Auto_Polymerization",
        "Documentation": "https://github.com/your-repo/Auto_Polymerization#readme",
    },
)