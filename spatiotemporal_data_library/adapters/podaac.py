import logging
import xarray as xr
import pandas as pd
import subprocess
from pathlib import Path
import os
from .base import DataSourceAdapter

NETRC_PATH = Path.home() / ".netrc"
CACHE_DIR = Path.home() / ".spatiotemporal_data_cache"

class PoDAACAdapterBase(DataSourceAdapter):
    """
    Base adapter for NASA PO.DAAC datasets.

    Handles authentication, request building, data download, parsing, and standardization for PO.DAAC datasets.
    """
    def _authenticate(self):
        """
        Check for Earthdata Login credentials file (~/.netrc).
        Logs a warning if missing.
        """
        if not NETRC_PATH.exists():
            logging.warning(f".netrc file not found at {NETRC_PATH}. Earthdata Login required. See PO.DAAC docs.")
        logging.info("PO.DAAC authentication: assuming .netrc file for Earthdata Login.")
    def _fetch_raw_data_podaac_subscriber(self, collection_short_name, start_date_str, end_date_str, bbox_str=None):
        """
        Download PO.DAAC data using podaac-data-downloader CLI.
        Args:
            collection_short_name (str): PO.DAAC collection short name.
            start_date_str (str): Start date string.
            end_date_str (str): End date string.
            bbox_str (str, optional): Bounding box string.
        Returns:
            list[Path]: List of downloaded NetCDF file paths.
        Raises:
            Exception: If download fails.
        """
        output_dir = CACHE_DIR / collection_short_name
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            'podaac-data-downloader',
            '-c', collection_short_name,
            '-d', str(output_dir),
            '--start-date', start_date_str,
            '--end-date', end_date_str,
        ]
        if bbox_str:
            cmd.extend(['-b', bbox_str])
        potential_cached_files = list(output_dir.glob('*.nc'))
        if potential_cached_files:
            logging.info(f"Found potential PO.DAAC files in cache: {output_dir}. Skipping download.")
            return potential_cached_files
        logging.info(f"Running podaac-data-downloader: {' '.join(cmd)}")
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if process.returncode != 0:
                logging.error(f"podaac-data-downloader failed, return code {process.returncode}: {process.stderr}")
                if "No granules found for" in process.stderr or "returned no results" in process.stderr:
                    logging.warning(f"No matching granules found: {collection_short_name}, {start_date_str} to {end_date_str}")
                    return
                raise subprocess.CalledProcessError(process.returncode, cmd, output=process.stdout, stderr=process.stderr)
            logging.info(process.stdout)
            downloaded_files = list(output_dir.glob('*.nc'))
            if not downloaded_files:
                logging.warning("No files downloaded by podaac-data-downloader, even though command succeeded.")
                return
            return downloaded_files
        except subprocess.CalledProcessError as e:
            logging.error(f"podaac-data-downloader failed: {e.stderr}")
            raise
        except FileNotFoundError:
            logging.error("podaac-data-downloader command not found. Please install and add to PATH.")
            raise NotImplementedError("podaac-data-downloader not available.")
    def _parse_data(self, raw_data_paths):
        """
        Parse PO.DAAC NetCDF files into an xarray.Dataset.
        Args:
            raw_data_paths (list[Path]): List of NetCDF file paths.
        Returns:
            xarray.Dataset: Parsed dataset.
        Raises:
            Exception: If parsing fails.
        """
        if not raw_data_paths:
            logging.info("No raw data paths provided to _parse_data, returning empty Dataset.")
            return xr.Dataset()
        try:
            if len(raw_data_paths) > 1:
                logging.info(f"Opening {len(raw_data_paths)} files as multi-file dataset.")
                str_paths = [str(p) for p in raw_data_paths]
                ds = xr.open_mfdataset(str_paths, combine='by_coords', engine='netcdf4', parallel=True, chunks={})
            else:
                ds = xr.open_dataset(raw_data_paths[0], engine='netcdf4', chunks={})
            return ds
        except Exception as e:
            logging.error(f"Error parsing PO.DAAC NetCDF files {raw_data_paths}: {e}")
            raise
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Standardize PO.DAAC dataset: rename coordinates to latitude/longitude if needed.
        Args:
            dataset (xarray.Dataset): Raw PO.DAAC dataset.
        Returns:
            xarray.Dataset: Standardized dataset.
        """
        rename_coords = {}
        if 'lat' in dataset.coords and 'latitude' not in dataset.coords:
            rename_coords['lat'] = 'latitude'
        if 'lon' in dataset.coords and 'longitude' not in dataset.coords:
            rename_coords['lon'] = 'longitude'
        dataset = dataset.rename(rename_coords)
        return dataset

class NOAACygnssL2Adapter(PoDAACAdapterBase):
    """
    Adapter for NOAA CYGNSS L2 wind speed data from PO.DAAC.
    """
    COLLECTION_SHORT_NAME = "CYGNN-22512"
    VARIABLE_MAP = {
        "surface_wind_speed": "wind_speed",
        "latitude": "lat",
        "longitude": "lon",
        "sample_time": "sample_time"
    }
    def _map_variables(self, standardized_vars):
        """
        Map standardized variable names to CYGNSS L2 native variable names.
        Args:
            standardized_vars (list[str]): List of standardized variable names.
        Returns:
            list[str]: List of native variable names.
        """
        return
    def _build_request_params(self):
        """
        Build request parameters for CYGNSS L2 download.
        Returns:
            dict: Request parameters for PoDAACAdapterBase._fetch_raw_data_podaac_subscriber.
        """
        start_date_str = self.start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date_str = self.end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        bbox_str = None
        if self.bbox:
            bbox_str = f"{self.bbox[0]},{self.bbox[1]},{self.bbox[2]},{self.bbox[3]}"
        return {
            "collection_short_name": self.COLLECTION_SHORT_NAME,
            "start_date_str": start_date_str,
            "end_date_str": end_date_str,
            "bbox_str": bbox_str
        }
    def _fetch_raw_data(self, request_params):
        """
        Download CYGNSS L2 data using PoDAACAdapterBase._fetch_raw_data_podaac_subscriber.
        Args:
            request_params (dict): Request parameters.
        Returns:
            list[Path]: List of downloaded NetCDF file paths.
        """
        return self._fetch_raw_data_podaac_subscriber(**request_params)
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Standardize CYGNSS L2 dataset: rename coordinates and variables if needed.
        Args:
            dataset (xarray.Dataset): Raw dataset.
        Returns:
            xarray.Dataset: Standardized dataset.
        """
        rename_map = {}
        if 'lat' in dataset and 'latitude' not in dataset: rename_map['lat'] = 'latitude'
        if 'lon' in dataset and 'longitude' not in dataset: rename_map['lon'] = 'longitude'
        if 'sample_time' in dataset and 'time' not in dataset: rename_map['sample_time'] = 'time'
        dataset = dataset.rename(rename_map)
        return dataset

class OSCARAdapter(PoDAACAdapterBase):
    """
    Adapter for OSCAR ocean current data from PO.DAAC.
    """
    COLLECTION_MAP = {
        "final": "OSCAR_L4_OC_FINAL_V2.0",
        "nrt": "OSCAR_L4_OC_NRT_V2.0",
        "interim": "OSCAR_L4_OC_INTERIM_V2.0"
    }
    VARIABLE_MAP = {
        "zonal_surface_current": "u",
        "meridional_surface_current": "v",
        "zonal_geostrophic_current": "ug",
        "meridional_geostrophic_current": "vg"
    }
    def __init__(self, dataset_name, variables, start_time, end_time, bbox=None, point=None, **kwargs):
        """
        Initialize OSCARAdapter with product type and collection mapping.
        Raises:
            ValueError: If oscar_product_type is invalid.
        """
        super().__init__(dataset_name, variables, start_time, end_time, bbox, point, **kwargs)
        self.product_type = self.kwargs.get('oscar_product_type', 'final').lower()
        if self.product_type not in self.COLLECTION_MAP:
            raise ValueError(f"Invalid oscar_product_type: {self.product_type}. Must be one of {list(self.COLLECTION_MAP.keys())}")
        self.collection_short_name = self.COLLECTION_MAP[self.product_type]
    def _map_variables(self, standardized_vars):
        """
        Map standardized variable names to OSCAR native variable names.
        Args:
            standardized_vars (list[str]): List of standardized variable names.
        Returns:
            list[str]: List of native variable names.
        """
        return
    def _build_request_params(self):
        """
        Build request parameters for OSCAR download.
        Returns:
            dict: Request parameters for PoDAACAdapterBase._fetch_raw_data_podaac_subscriber.
        """
        start_date_str = self.start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date_str = self.end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        bbox_str = None
        if self.bbox:
            bbox_str = f"{self.bbox[0]},{self.bbox[1]},{self.bbox[2]},{self.bbox[3]}"
        return {
            "collection_short_name": self.collection_short_name,
            "start_date_str": start_date_str,
            "end_date_str": end_date_str,
            "bbox_str": bbox_str
        }
    def _fetch_raw_data(self, request_params):
        """
        Download OSCAR data using PoDAACAdapterBase._fetch_raw_data_podaac_subscriber.
        Args:
            request_params (dict): Request parameters.
        Returns:
            list[Path]: List of downloaded NetCDF file paths.
        """
        return self._fetch_raw_data_podaac_subscriber(**request_params)
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Standardize OSCAR dataset: rename coordinates if needed.
        Args:
            dataset (xarray.Dataset): Raw dataset.
        Returns:
            xarray.Dataset: Standardized dataset.
        """
        rename_map = {}
        if 'latitude' not in dataset.coords and 'lat' in dataset.coords:
            rename_map['lat'] = 'latitude'
        if 'longitude' not in dataset.coords and 'lon' in dataset.coords:
            rename_map['lon'] = 'longitude'
        dataset = dataset.rename(rename_map)
        return dataset 