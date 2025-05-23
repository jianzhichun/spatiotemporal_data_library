from setuptools import setup, find_packages

setup(
    name="spatiotemporal_data_library",
    version="0.1.1",
    description="A Python library for unified access to multi-source spatiotemporal Earth observation data (ERA5, PO.DAAC, SMAP, SFMR, etc.)",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/spatiotemporal_data_library",
    license="MIT",
    keywords=["spatiotemporal", "earth observation", "remote sensing", "ERA5", "PO.DAAC", "SMAP", "SFMR", "xarray", "meteorology", "oceanography"],
    project_urls={
        "Documentation": "https://github.com/yourusername/spatiotemporal_data_library",
        "Source": "https://github.com/yourusername/spatiotemporal_data_library",
        "Tracker": "https://github.com/yourusername/spatiotemporal_data_library/issues"
    },
    packages=find_packages(),
    install_requires=[
        "xarray>=2022.0",
        "pandas>=1.3",
        "requests>=2.25",
        "cdsapi>=0.5",
        "netCDF4>=1.5"
    ],
    extras_require={
        "test": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "xarray>=2022.0",
            "pandas>=1.3",
            "requests>=2.25",
            "cdsapi>=0.5",
            "netCDF4>=1.5"
        ],
    },
    python_requires=">=3.8",
    include_package_data=True,
    package_data={"": ["requirements.txt", "README.md", "README_zh.md"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Natural Language :: Chinese (Simplified)"
    ],
    entry_points={
        # Optional: provide CLI entry points here
    },
) 