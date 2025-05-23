import logging
import pandas as pd
import xarray as xr
import cdsapi
from .base import DataSourceAdapter
from pathlib import Path
import os

CDSAPIRC_PATH = Path.home() / ".cdsapirc"
CACHE_DIR = Path.home() / ".spatiotemporal_data_cache"

class ERA5Adapter(DataSourceAdapter):
    """
    Adapter for ECMWF ERA5 reanalysis data.

    Handles authentication, request building, data download, parsing, and standardization for ERA5.
    """
    DATASET_ID_SINGLE_LEVELS = 'reanalysis-era5-single-levels'
    VARIABLE_MAP = {
        "10m_u_component_of_wind": "10m_u_component_of_wind",
        "10m_v_component_of_wind": "10m_v_component_of_wind",
        "significant_wave_height": "significant_height_of_combined_wind_waves_and_swell",
        "surface_wind_speed": "calculated_wind_speed"
    }
    def _map_variables(self, standardized_vars):
        """
        Map standardized variable names to ERA5 native variable names.

        Args:
            standardized_vars (list[str]): List of standardized variable names.
        Returns:
            list[str]: List of native ERA5 variable names.
        """
        native_vars = set()
        self.needs_wind_speed_calculation = False
        for var in standardized_vars:
            if var == "surface_wind_speed":
                native_vars.add(self.VARIABLE_MAP["10m_u_component_of_wind"])
                native_vars.add(self.VARIABLE_MAP["10m_v_component_of_wind"])
                self.needs_wind_speed_calculation = True
            elif var in self.VARIABLE_MAP:
                native_vars.add(self.VARIABLE_MAP[var])
            else:
                logging.warning(f"Variable '{var}' not explicitly mapped in ERA5. Using as is.")
                native_vars.add(var)
        return list(native_vars)
    def _authenticate(self):
        """
        Check for CDS API credentials file (~/.cdsapirc).
        Raises:
            FileNotFoundError: If the credentials file is missing.
        """
        if not CDSAPIRC_PATH.exists():
            logging.error(f"CDS API config file not found at {CDSAPIRC_PATH}. See: https://cds.climate.copernicus.eu/api-how-to")
            raise FileNotFoundError(f"CDS API config file not found: {CDSAPIRC_PATH}")
        logging.info("CDS API authentication: assuming .cdsapirc is configured.")
    def _build_request_params(self):
        """
        Build request parameters for the ERA5 CDS API.
        Returns:
            dict: Request parameters for cdsapi.Client().retrieve().
        """
        dates = pd.date_range(self.start_time.date(), self.end_time.date(), freq='D')
        years = sorted(list(set([str(d.year) for d in dates])))
        months = sorted(list(set([f"{d.month:02d}" for d in dates])))
        days = sorted(list(set([f"{d.day:02d}" for d in dates])))
        if self.start_time.date() == self.end_time.date():
            times = [f"{h:02d}:00" for h in range(self.start_time.hour, self.end_time.hour + 1)]
        else:
            times = [f"{h:02d}:00" for h in range(24)]
        request = {
            'product_type': 'reanalysis',
            'variable': self.native_variables,
            'year': years,
            'month': months,
            'day': days,
            'time': times,
            'format': 'netcdf',
        }
        if self.bbox:
            request['area'] = [self.bbox[1], self.bbox[0], self.bbox[3], self.bbox[2]]
        if 'pressure_level' in self.kwargs:
            request['pressure_level'] = self.kwargs['pressure_level']
        return request
    def _fetch_raw_data(self, request_params):
        """
        Download ERA5 data using cdsapi.Client().
        Args:
            request_params (dict): Request parameters for cdsapi.
        Returns:
            Path: Path to the downloaded NetCDF file.
        Raises:
            Exception: If download fails.
        """
        client = cdsapi.Client()
        param_hash = abs(hash(frozenset(request_params.items())))
        target_filename = CACHE_DIR / f"era5_{param_hash}.nc"
        if target_filename.exists():
            logging.info(f"Found ERA5 data in cache: {target_filename}")
            return target_filename
        logging.info(f"Requesting ERA5 data: {request_params}")
        try:
            client.retrieve(
                self.DATASET_ID_SINGLE_LEVELS,
                request_params,
                str(target_filename)
            )
            logging.info(f"ERA5 data downloaded to {target_filename}")
            return target_filename
        except Exception as e:
            logging.error(f"Error downloading ERA5 data: {e}")
            raise
    def _parse_data(self, raw_data_path):
        """
        Parse ERA5 NetCDF file into an xarray.Dataset.
        Args:
            raw_data_path (Path): Path to the NetCDF file.
        Returns:
            xarray.Dataset: Parsed dataset.
        Raises:
            Exception: If parsing fails.
        """
        try:
            ds = xr.open_dataset(raw_data_path, engine='netcdf4')
            return ds
        except Exception as e:
            logging.error(f"Error parsing ERA5 NetCDF file {raw_data_path}: {e}")
            raise
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Standardize ERA5 dataset: calculate wind speed if needed, rename coordinates.
        Args:
            dataset (xarray.Dataset): Raw ERA5 dataset.
        Returns:
            xarray.Dataset: Standardized dataset.
        """
        if self.needs_wind_speed_calculation:
            u_var_name = self.VARIABLE_MAP["10m_u_component_of_wind"]
            v_var_name = self.VARIABLE_MAP["10m_v_component_of_wind"]
            if u_var_name in dataset and v_var_name in dataset:
                dataset['surface_wind_speed'] = xr.ufuncs.sqrt(dataset[u_var_name]**2 + dataset[v_var_name]**2)
                dataset['surface_wind_speed'].attrs['units'] = 'm s-1'
                dataset['surface_wind_speed'].attrs['long_name'] = '10m Wind Speed'
                if "10m_u_component_of_wind" not in self.raw_variables_requested:
                    dataset = dataset.drop_vars([u_var_name], errors='ignore')
                if "10m_v_component_of_wind" not in self.raw_variables_requested:
                    dataset = dataset.drop_vars([v_var_name], errors='ignore')
            else:
                logging.warning("Requested surface_wind_speed, but u/v components missing in ERA5 dataset.")
        rename_coords = {}
        if 'longitude' in dataset.coords and 'lon' not in dataset.coords:
            rename_coords['longitude'] = 'lon'
        if 'latitude' in dataset.coords and 'lat' not in dataset.coords:
            rename_coords['latitude'] = 'lat'
        dataset = dataset.rename(rename_coords)
        return dataset 