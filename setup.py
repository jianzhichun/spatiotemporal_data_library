from setuptools import setup, find_packages

setup(
    name="spatiotemporal_data_library",
    version="0.1.0",
    description="统一获取多源时空地球观测数据的 Python 库 (ERA5, PO.DAAC, SMAP, SFMR 等)",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/spatiotemporal_data_library",
    packages=find_packages(),
    install_requires=[
        "xarray>=2022.0",
        "pandas>=1.3",
        "requests>=2.25",
        "cdsapi>=0.5",
        "netCDF4>=1.5"
    ],
    extras_require={
        "test": ["pytest>=7.0"],
    },
    python_requires=">=3.8",
    include_package_data=True,
    package_data={"": ["requirements.txt", "README.md"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        # 可选: 提供命令行接口
    },
) 