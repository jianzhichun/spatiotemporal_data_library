# spatiotemporal_data_library

## Introduction

`spatiotemporal_data_library` is a Python library for unified access to multi-source spatiotemporal Earth observation data, supporting major meteorological and oceanographic datasets such as ERA5, PO.DAAC (e.g., CYGNSS, OSCAR), SMAP RSS, and SFMR. Through a unified interface, users can easily search, download, parse, and standardize various remote sensing and reanalysis data.

## Installation

It is recommended to use conda or pip to install dependencies:

```bash
pip install xarray pandas requests cdsapi netCDF4
# For PO.DAAC support, make sure podaac-data-downloader is installed and .netrc is configured
# For ERA5 support, configure .cdsapirc
```

## Directory Structure

```
spatiotemporal_data_library/
├── __init__.py
├── fetch.py           # Main entry fetch_data
├── adapters/          # Data source adapters
├── utils.py           # Utility functions
├── config.py          # Configuration
└── test_spatiotemporal_data_library.py  # Test cases
```

## Quick Start

```python
from spatiotemporal_data_library import fetch_data
import datetime

ds = fetch_data(
    dataset_short_name="ECMWF_ERA5",
    variables=["10m_u_component_of_wind", "10m_v_component_of_wind"],
    start_time="2023-01-01T00:00:00Z",
    end_time="2023-01-01T03:00:00Z",
    bbox=[-5, 50, 0, 52]  # [min_lon, min_lat, max_lon, max_lat]
)
print(ds)
```

## API Reference

### fetch_data

```python
def fetch_data(dataset_short_name: str,
               variables: list[str],
               start_time: str | datetime.datetime,
               end_time: str | datetime.datetime,
               bbox: list[float] = None,
               point: list[float] = None,
               **kwargs) -> xr.Dataset:
```
- **dataset_short_name**: Dataset short name (see table below)
- **variables**: List of standardized variable names
- **start_time/end_time**: Query time (ISO string or datetime object)
- **bbox**: Optional, geographic bounding box [min_lon, min_lat, max_lon, max_lat]
- **point**: Optional, single point [lon, lat]
- **kwargs**: Adapter-specific parameters (e.g., pressure_level, storm_name, mission_id, etc.)

Returns: `xarray.Dataset`, standardized dataset

### Supported Datasets and Parameters

| Name                | dataset_short_name         | Example Main Variables         | Note |
|---------------------|---------------------------|-------------------------------|------|
| ERA5                | ECMWF_ERA5                | 10m_u_component_of_wind, ...  | Requires .cdsapirc |
| NOAA CYGNSS L2      | NOAA_CYGNSS_L2_V1.2       | surface_wind_speed, ...       | Requires podaac-data-downloader, .netrc |
| OSCAR V2 FINAL/NRT  | OSCAR_V2_FINAL/OSCAR_V2_NRT| zonal_surface_current, ...    | Requires podaac-data-downloader, .netrc |
| SMAP L3 RSS FINAL   | SMAP_L3_RSS_FINAL         | surface_wind_speed            | Requires FTP account |
| SFMR HRD            | SFMR_HRD                  | surface_wind_speed, rain_rate | Public/Some require mission_id |

For detailed variables and parameters, see the source code of each adapter.

## Caching Mechanism

- All downloaded raw data files are cached by default in the `~/.spatiotemporal_data_cache` directory.
- Files will not be re-downloaded if they already exist.
- You can manually clear this directory to free up space.

## Dependencies
- `xarray`, `pandas`, `requests`, `cdsapi`, `netCDF4`
- ERA5 requires configuration of `~/.cdsapirc`, see [CDS API Documentation](https://cds.climate.copernicus.eu/api-how-to)
- PO.DAAC requires configuration of `~/.netrc`, see [Earthdata Login](https://urs.earthdata.nasa.gov/)
- SMAP RSS requires applying for an FTP account and setting the environment variables `RSS_FTP_USER` and `RSS_FTP_PASSWORD`
- SFMR public data does not require authentication, some require mission_id

## Testing

```bash
pip install pytest
pytest spatiotemporal_data_library/test_spatiotemporal_data_library.py
```

## Contribution & Feedback

Issues, PRs, and suggestions via email are welcome. 