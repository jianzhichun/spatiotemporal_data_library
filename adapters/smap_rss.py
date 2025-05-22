import logging
import xarray as xr
import os
import ftplib
import datetime
from pathlib import Path
from .base import DataSourceAdapter

CACHE_DIR = Path.home() / ".spatiotemporal_data_cache"

class SMAPRSSAdapter(DataSourceAdapter):
    BASE_FTP_URL = "ftp.remss.com"
    VARIABLE_MAP = {
        "surface_wind_speed": "wind",
        "time_of_day_utc_minute": "minute"
    }
    def _map_variables(self, standardized_vars):
        return
    def _authenticate(self):
        self.ftp_user = os.getenv("RSS_FTP_USER")
        self.ftp_password = os.getenv("RSS_FTP_PASSWORD")
        if not self.ftp_user or not self.ftp_password:
            logging.warning("在环境变量 (RSS_FTP_USER, RSS_FTP_PASSWORD) 中未找到 RSS FTP 凭据。FTP 访问将失败。")
        logging.info("SMAP RSS: 如果已设置，将使用 FTP 认证凭据。")
    def _build_request_params(self):
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
        downloaded_files = []
        for file_info in request_params_list:
            target_file = CACHE_DIR / file_info["filename"]
            if target_file.exists():
                logging.info(f"在缓存中找到 SMAP RSS 数据: {target_file}")
                downloaded_files.append(target_file)
                continue
            if file_info["type"] == "ftp":
                if not self.ftp_user or not self.ftp_password:
                    logging.error("SMAP RSS 的 FTP 凭据不可用。跳过下载。")
                    continue
                try:
                    logging.info(f"尝试 FTP 下载: ftp://{self.BASE_FTP_URL}{file_info['path']}")
                    with ftplib.FTP(self.BASE_FTP_URL) as ftp:
                        ftp.login(self.ftp_user, self.ftp_password)
                        with open(target_file, 'wb') as fp:
                            ftp.retrbinary(f"RETR {file_info['path']}", fp.write)
                        logging.info(f"已将 {file_info['filename']} 下载到 {target_file}")
                        downloaded_files.append(target_file)
                except Exception as e:
                    logging.error(f"FTP 下载 {file_info['filename']} 失败: {e}")
                    if target_file.exists(): target_file.unlink()
            elif file_info["type"] == "https":
                logging.warning("SMAP RSS 的 HTTPS 下载在此示例中未完全实现。")
                pass
        if not downloaded_files:
            raise FileNotFoundError("未成功下载或在缓存中找到 SMAP RSS 文件。")
        return downloaded_files
    def _parse_data(self, raw_data_paths):
        if not raw_data_paths:
            raise ValueError("未向 SMAP RSS 的 _parse_data 提供数据路径。")
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
            logging.error(f"解析 SMAP RSS NetCDF 文件 {raw_data_paths} 时出错: {e}")
            raise
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        rename_coords = {}
        dataset = dataset.rename(rename_coords)
        return dataset 