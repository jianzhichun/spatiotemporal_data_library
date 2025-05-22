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
    def _authenticate(self):
        if not NETRC_PATH.exists():
            logging.warning(f".netrc 文件未在 {NETRC_PATH} 找到。Earthdata Login 需要此文件。请参阅 PO.DAAC 文档。")
        logging.info("PO.DAAC 认证: 假定为 Earthdata Login 使用.netrc 文件。")
    def _fetch_raw_data_podaac_subscriber(self, collection_short_name, start_date_str, end_date_str, bbox_str=None):
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
            logging.info(f"在缓存目录 {output_dir} 中找到潜在的 PO.DAAC 文件。跳过下载。")
            return potential_cached_files
        logging.info(f"执行 podaac-data-downloader: {' '.join(cmd)}")
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if process.returncode != 0:
                logging.error(f"podaac-data-downloader 失败，返回码 {process.returncode}: {process.stderr}")
                if "No granules found for" in process.stderr or "returned no results" in process.stderr:
                    logging.warning(f"podaac-data-downloader 未找到与请求匹配的granules: {collection_short_name}, {start_date_str} to {end_date_str}")
                    return
                raise subprocess.CalledProcessError(process.returncode, cmd, output=process.stdout, stderr=process.stderr)
            logging.info(process.stdout)
            downloaded_files = list(output_dir.glob('*.nc'))
            if not downloaded_files:
                logging.warning("podaac-data-downloader 未下载任何文件，即使命令成功。可能没有匹配的数据。")
                return
            return downloaded_files
        except subprocess.CalledProcessError as e:
            logging.error(f"podaac-data-downloader 失败: {e.stderr}")
            raise
        except FileNotFoundError:
            logging.error("未找到 podaac-data-downloader 命令。请确保已安装并在 PATH 中。")
            raise NotImplementedError("podaac-data-downloader 不可用。")
    def _parse_data(self, raw_data_paths):
        if not raw_data_paths:
            logging.info("没有提供原始数据路径给 _parse_data，返回空 Dataset。")
            return xr.Dataset()
        try:
            if len(raw_data_paths) > 1:
                logging.info(f"将 {len(raw_data_paths)} 个文件作为多文件数据集打开。")
                str_paths = [str(p) for p in raw_data_paths]
                ds = xr.open_mfdataset(str_paths, combine='by_coords', engine='netcdf4', parallel=True, chunks={})
            else:
                ds = xr.open_dataset(raw_data_paths[0], engine='netcdf4', chunks={})
            return ds
        except Exception as e:
            logging.error(f"解析 PO.DAAC NetCDF 文件 {raw_data_paths} 时出错: {e}")
            raise
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        rename_coords = {}
        if 'lat' in dataset.coords and 'latitude' not in dataset.coords:
            rename_coords['lat'] = 'latitude'
        if 'lon' in dataset.coords and 'longitude' not in dataset.coords:
            rename_coords['lon'] = 'longitude'
        dataset = dataset.rename(rename_coords)
        return dataset

class NOAACygnssL2Adapter(PoDAACAdapterBase):
    COLLECTION_SHORT_NAME = "CYGNN-22512"
    VARIABLE_MAP = {
        "surface_wind_speed": "wind_speed",
        "latitude": "lat",
        "longitude": "lon",
        "sample_time": "sample_time"
    }
    def _map_variables(self, standardized_vars):
        return
    def _build_request_params(self):
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
        return self._fetch_raw_data_podaac_subscriber(**request_params)
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        rename_map = {}
        if 'lat' in dataset and 'latitude' not in dataset: rename_map['lat'] = 'latitude'
        if 'lon' in dataset and 'longitude' not in dataset: rename_map['lon'] = 'longitude'
        if 'sample_time' in dataset and 'time' not in dataset: rename_map['sample_time'] = 'time'
        dataset = dataset.rename(rename_map)
        return dataset

class OSCARAdapter(PoDAACAdapterBase):
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
        super().__init__(dataset_name, variables, start_time, end_time, bbox, point, **kwargs)
        self.product_type = self.kwargs.get('oscar_product_type', 'final').lower()
        if self.product_type not in self.COLLECTION_MAP:
            raise ValueError(f"无效的 oscar_product_type: {self.product_type}。必须是 {list(self.COLLECTION_MAP.keys())} 中的一个")
        self.collection_short_name = self.COLLECTION_MAP[self.product_type]
    def _map_variables(self, standardized_vars):
        return
    def _build_request_params(self):
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
        return self._fetch_raw_data_podaac_subscriber(**request_params)
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        rename_map = {}
        if 'latitude' not in dataset.coords and 'lat' in dataset.coords:
            rename_map['lat'] = 'latitude'
        if 'longitude' not in dataset.coords and 'lon' in dataset.coords:
            rename_map['lon'] = 'longitude'
        dataset = dataset.rename(rename_map)
        return dataset 