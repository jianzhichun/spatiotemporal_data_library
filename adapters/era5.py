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
    DATASET_ID_SINGLE_LEVELS = 'reanalysis-era5-single-levels'
    VARIABLE_MAP = {
        "10m_u_component_of_wind": "10m_u_component_of_wind",
        "10m_v_component_of_wind": "10m_v_component_of_wind",
        "significant_wave_height": "significant_height_of_combined_wind_waves_and_swell",
        "surface_wind_speed": "calculated_wind_speed"
    }
    def _map_variables(self, standardized_vars):
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
                logging.warning(f"变量 '{var}' 未在 ERA5 中显式映射。将按原样使用。")
                native_vars.add(var)
        return list(native_vars)
    def _authenticate(self):
        if not CDSAPIRC_PATH.exists():
            logging.error(f"CDS API 配置文件未在 {CDSAPIRC_PATH} 找到。请创建它。参见: https://cds.climate.copernicus.eu/api-how-to")
            raise FileNotFoundError(f"CDS API 配置文件未找到: {CDSAPIRC_PATH}")
        logging.info("CDS API 认证: 假定.cdsapirc 文件已配置。")
    def _build_request_params(self):
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
        client = cdsapi.Client()
        param_hash = abs(hash(frozenset(request_params.items())))
        target_filename = CACHE_DIR / f"era5_{param_hash}.nc"
        if target_filename.exists():
            logging.info(f"在缓存中找到 ERA5 数据: {target_filename}")
            return target_filename
        logging.info(f"请求 ERA5 数据: {request_params}")
        try:
            client.retrieve(
                self.DATASET_ID_SINGLE_LEVELS,
                request_params,
                str(target_filename)
            )
            logging.info(f"ERA5 数据已下载到 {target_filename}")
            return target_filename
        except Exception as e:
            logging.error(f"下载 ERA5 数据时出错: {e}")
            raise
    def _parse_data(self, raw_data_path):
        try:
            ds = xr.open_dataset(raw_data_path, engine='netcdf4')
            return ds
        except Exception as e:
            logging.error(f"解析 ERA5 NetCDF 文件 {raw_data_path} 时出错: {e}")
            raise
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
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
                logging.warning("请求了 surface_wind_speed，但 ERA5 数据集中缺少 u/v 分量。")
        rename_coords = {}
        if 'longitude' in dataset.coords and 'lon' not in dataset.coords:
            rename_coords['longitude'] = 'lon'
        if 'latitude' in dataset.coords and 'lat' not in dataset.coords:
            rename_coords['latitude'] = 'lat'
        dataset = dataset.rename(rename_coords)
        return dataset 