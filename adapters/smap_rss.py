import logging
import xarray as xr
import os
import ftplib
import datetime
from pathlib import Path
from .base import DataSourceAdapter

CACHE_DIR = Path.home() / ".spatiotemporal_data_cache"

class SMAPRSSAdapter(DataSourceAdapter):
    """
    Adapter for SMAP L3 RSS wind speed data.

    Handles authentication, FTP download, parsing, and standardization for SMAP RSS.
    """
    BASE_FTP_URL = "ftp.remss.com"
    VARIABLE_MAP = {
        "surface_wind_speed": "wind",
        "time_of_day_utc_minute": "minute"
    }
    def _map_variables(self, standardized_vars):
        """
        Map standardized variable names to SMAP RSS native variable names.
        Args:
            standardized_vars (list[str]): List of standardized variable names.
        Returns:
            list[str]: List of native variable names.
        """
        return
    def _authenticate(self):
        """
        Check for FTP credentials in environment variables (RSS_FTP_USER, RSS_FTP_PASSWORD).
        Logs a warning if missing.
        """
        self.ftp_user = os.getenv("RSS_FTP_USER")
        self.ftp_password = os.getenv("RSS_FTP_PASSWORD")
        if not self.ftp_user or not self.ftp_password:
            logging.warning("RSS FTP credentials not found in environment variables (RSS_FTP_USER, RSS_FTP_PASSWORD). FTP access will fail.")
        logging.info("SMAP RSS: Will use FTP credentials if set.")
    def _build_request_params(self):
        """
        Build request parameters (file list) for SMAP RSS FTP download.
        Returns:
            list[dict]: List of file info dicts for download.
        """
        file_list = []
        current_date = self.start_time.date()
        end_date_boundary = self.end_time.date()
        while current_date <= end_date_boundary:
            year = f"{current_date.year:04d}"
            month = f"{current_date.month:02d}"
            day_str = f"{current_date.day:02d}"
            filename = f"rss_smap_L3_daily_winds_v01.0_final_{year}{month}{day_str}.nc"
            ftp_path_corrected = f"/smap/wind/v01.0/daily/final/{year}/{month}/{filename}"
            file_list.append({"type": "ftp", "path": ftp_path_corrected, "date": current_date, "filename": filename})
            current_date += datetime.timedelta(days=1)
        return file_list
    def _fetch_raw_data(self, request_params_list):
        """
        Download SMAP RSS files via FTP.
        Args:
            request_params_list (list[dict]): List of file info dicts.
        Returns:
            list[Path]: List of downloaded NetCDF file paths.
        Raises:
            FileNotFoundError: If no files are downloaded or found in cache.
        """
        downloaded_files = []
        for file_info in request_params_list:
            target_file = CACHE_DIR / file_info["filename"]
            if target_file.exists():
                logging.info(f"Found SMAP RSS data in cache: {target_file}")
                downloaded_files.append(target_file)
                continue
            if file_info["type"] == "ftp":
                if not self.ftp_user or not self.ftp_password:
                    logging.error("FTP credentials for SMAP RSS are not available. Skipping download.")
                    continue
                try:
                    logging.info(f"Attempting FTP download: ftp://{self.BASE_FTP_URL}{file_info['path']}")
                    with ftplib.FTP(self.BASE_FTP_URL) as ftp:
                        ftp.login(self.ftp_user, self.ftp_password)
                        with open(target_file, 'wb') as fp:
                            ftp.retrbinary(f"RETR {file_info['path']}", fp.write)
                        logging.info(f"Downloaded {file_info['filename']} to {target_file}")
                        downloaded_files.append(target_file)
                except Exception as e:
                    logging.error(f"FTP download failed for {file_info['filename']}: {e}")
                    if target_file.exists(): target_file.unlink()
            elif file_info["type"] == "https":
                logging.warning("HTTPS download for SMAP RSS not fully implemented in this example.")
                pass
        if not downloaded_files:
            raise FileNotFoundError("No SMAP RSS files downloaded or found in cache.")
        return downloaded_files
    def _parse_data(self, raw_data_paths):
        """
        Parse SMAP RSS NetCDF files into an xarray.Dataset.
        Args:
            raw_data_paths (list[Path]): List of NetCDF file paths.
        Returns:
            xarray.Dataset: Parsed dataset.
        Raises:
            Exception: If parsing fails.
        """
        if not raw_data_paths:
            raise ValueError("No data paths provided to SMAP RSS _parse_data.")
        try:
            str_paths = [str(p) for p in raw_data_paths]
            def preprocess_smap_rss(ds):
                filename = Path(ds.encoding["source"]).name
                date_str = filename.split('_')[-1].split('.')[0]
                file_date = datetime.datetime.strptime(date_str, "%Y%m%d")
                ds = ds.assign_coords(time=file_date)
                ds = ds.expand_dims('time')
                return ds
            ds = xr.open_mfdataset(str_paths, combine='nested', concat_dim='time', engine='netcdf4', preprocess=preprocess_smap_rss)
            ds = ds.sortby('time')
            return ds
        except Exception as e:
            logging.error(f"Error parsing SMAP RSS NetCDF files {raw_data_paths}: {e}")
            raise
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Standardize SMAP RSS dataset (currently a passthrough).
        Args:
            dataset (xarray.Dataset): Raw dataset.
        Returns:
            xarray.Dataset: Standardized dataset.
        """
        rename_coords = {}
        dataset = dataset.rename(rename_coords)
        return dataset 