import logging
import xarray as xr
import pandas as pd
import requests
import gzip
import os
from pathlib import Path
from .base import DataSourceAdapter

CACHE_DIR = Path.home() / ".spatiotemporal_data_cache"

class SFMRAdapter(DataSourceAdapter):
    """
    Adapter for SFMR (Stepped Frequency Microwave Radiometer) wind and rain data.

    Handles authentication, request building, download, parsing, and standardization for SFMR datasets.
    """
    # 对于 ASCII V1/V2 [8]
    ASCII_V1_COLS = ["Date", "Time", "Lat", "Lon", "Sfc_WS", "RR"]
    ASCII_V2_COLS = ["Date", "Time", "Lat", "Lon", "Sfc_WS", "RR"]
    NETCDF_VAR_MAP = {
        "surface_wind_speed": "SWS",
        "rain_rate": "SRR",
        "latitude": "LAT",
        "longitude": "LON",
        "time_utc": "TIME",
        "date_yyyymmdd": "DATE"
    }
    def _map_variables(self, standardized_vars):
        """
        Map standardized variable names to SFMR native variable names.
        Args:
            standardized_vars (list[str]): List of standardized variable names.
        Returns:
            list[str]: List of native variable names.
        """
        return
    def _authenticate(self):
        """
        SFMR HRD data is usually public; no authentication required.
        Logs info about data policy for Type 3 data.
        """
        logging.info("SFMR HRD data: usually public, no specific API key required. Check data policy for Type 3 data.")
    def _build_request_params(self):
        """
        Build request parameters (URL, filename, file_type) for SFMR download.
        Returns:
            dict: Request parameters for download.
        Raises:
            ValueError: If required parameters are missing.
        """
        storm_name = self.kwargs.get('storm_name')
        year_str = str(self.kwargs.get('year', self.start_time.year))
        mission_id = self.kwargs.get('mission_id')
        if not storm_name or not year_str:
            raise ValueError("SFMR requires 'storm_name' and 'year' in kwargs.")
        file_type = self.kwargs.get('sfmr_file_type', 'netcdf').lower()
        filename_stem = self.kwargs.get('filename_stem')
        if not filename_stem and mission_id:
            filename_stem = f"NOAA_SFMR{mission_id}"
        if not filename_stem:
            raise ValueError("For SFMR, provide 'mission_id' (e.g. '20190828H1') or 'filename_stem' (e.g. 'NOAA_SFMR20190828H1') in kwargs.")
        if file_type == 'netcdf':
            filename = f"{filename_stem}.nc"
        elif file_type.startswith('ascii'):
            filename = f"{filename_stem}.dat.gz"
        else:
            raise ValueError(f"Unsupported SFMR file type: {file_type}")
        url = f"https://www.aoml.noaa.gov/hrd/Storm_pages/{storm_name.upper()}{year_str}/data/sfmr/{filename}"
        return {"url": url, "filename": filename, "file_type": file_type}
    def _fetch_raw_data(self, request_params):
        """
        Download SFMR data from NOAA HRD.
        Args:
            request_params (dict): Request parameters (URL, filename, file_type).
        Returns:
            Path: Path to the downloaded file.
        Raises:
            FileNotFoundError: If download fails.
        """
        url = request_params["url"]
        filename = request_params["filename"]
        target_file = CACHE_DIR / filename
        if target_file.exists():
            logging.info(f"Found SFMR data in cache: {target_file}")
            return target_file
        logging.info(f"Downloading SFMR data from: {url}")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(target_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"SFMR data downloaded to {target_file}")
            return target_file
        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading SFMR data from {url}: {e}")
            if target_file.exists(): target_file.unlink()
            raise FileNotFoundError(f"Failed to download SFMR data from {url}. Check URL and availability.")
    def _parse_data(self, raw_data_path):
        """
        Parse SFMR NetCDF or ASCII file into an xarray.Dataset.
        Args:
            raw_data_path (Path): Path to the downloaded file.
        Returns:
            xarray.Dataset: Parsed dataset.
        Raises:
            Exception: If parsing fails.
        """
        file_type = self.kwargs.get('sfmr_file_type', 'netcdf').lower()
        try:
            if file_type == 'netcdf':
                ds = xr.open_dataset(raw_data_path, engine='netcdf4', chunks={})
            elif file_type.startswith('ascii'):
                col_names = self.ASCII_V2_COLS if file_type == 'ascii_v2' else self.ASCII_V1_COLS
                with gzip.open(raw_data_path, 'rt') as f:
                    df = pd.read_csv(f, delim_whitespace=True, names=col_names, na_values=[-99.9, -999, -9999.0, -99.90], comment='#')
                df['datetime_str'] = df['Date'].astype(str) + df['Time'].astype(str).str.zfill(6)
                df['time_coord'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d%H%M%S')
                df = df.set_index('time_coord')
                ds = xr.Dataset.from_dataframe(df)
                rename_map_ascii = {'Sfc_WS': 'SWS', 'RR': 'SRR', 'Lat':'LAT', 'Lon':'LON', 'Time':'TIME_int', 'Date':'DATE_int'}
                ds = ds.rename({k:v for k,v in rename_map_ascii.items() if k in ds})
            else:
                raise ValueError(f"Unsupported SFMR file type: {file_type}")
            return ds
        except Exception as e:
            logging.error(f"Error parsing SFMR file {raw_data_path} (type: {file_type}): {e}")
            raise
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Standardize SFMR dataset: rename variables and coordinates to standard names.
        Args:
            dataset (xarray.Dataset): Raw dataset.
        Returns:
            xarray.Dataset: Standardized dataset.
        """
        rename_vars = {}
        for std_name, native_name in self.NETCDF_VAR_MAP.items():
            if native_name in dataset and std_name != native_name:
                rename_vars[native_name] = std_name
        dataset = dataset.rename(rename_vars)
        rename_coords = {}
        if 'LAT' in dataset.coords and 'latitude' not in dataset.coords: rename_coords['LAT'] = 'latitude'
        if 'LON' in dataset.coords and 'longitude' not in dataset.coords: rename_coords['LON'] = 'longitude'
        if 'TIME_int' in dataset and 'DATE_int' in dataset and 'time' not in dataset.coords:
            if 'time_coord' in dataset.indexes:
                dataset = dataset.rename({'time_coord': 'time'})
        dataset = dataset.rename(rename_coords)
        if 'time' in dataset.coords and 'time' not in dataset.dims and len(dataset.dims)>0:
            dataset = dataset.swap_dims({list(dataset.dims)[0]: 'time'})
        return dataset 