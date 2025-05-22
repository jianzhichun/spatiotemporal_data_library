# spatiotemporal_data_library

## 简介

`spatiotemporal_data_library` 是一个用于统一获取多源时空地球观测数据的 Python 库，支持 ERA5、PO.DAAC（如 CYGNSS、OSCAR）、SMAP RSS、SFMR 等主流气象与海洋数据集。通过统一接口，用户可便捷地检索、下载、解析并标准化各类遥感与再分析数据。

## 安装

建议使用 conda 或 pip 安装依赖：

```bash
pip install xarray pandas requests cdsapi netCDF4
# 如需 PO.DAAC 支持，请确保已安装 podaac-data-downloader 并配置 .netrc
# 如需 ERA5 支持，请配置 .cdsapirc
```

## 目录结构

```
spatiotemporal_data_library/
├── __init__.py
├── fetch.py           # 主入口 fetch_data
├── adapters/          # 各数据源适配器
├── utils.py           # 工具函数
├── config.py          # 配置
└── test_spatiotemporal_data_library.py  # 测试用例
```

## 快速开始

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

## API 说明

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
- **dataset_short_name**: 数据集短名称（见下表）
- **variables**: 标准化变量名列表
- **start_time/end_time**: 查询时间（ISO字符串或datetime对象）
- **bbox**: 可选，地理范围 [min_lon, min_lat, max_lon, max_lat]
- **point**: 可选，单点 [lon, lat]
- **kwargs**: 适配器特定参数（如 pressure_level, storm_name, mission_id 等）

返回：`xarray.Dataset`，标准化后的数据集

### 支持的数据集及参数

| 名称                | dataset_short_name         | 主要变量示例                  | 备注 |
|---------------------|---------------------------|-------------------------------|------|
| ERA5                | ECMWF_ERA5                | 10m_u_component_of_wind, ...  | 需 .cdsapirc |
| NOAA CYGNSS L2      | NOAA_CYGNSS_L2_V1.2       | surface_wind_speed, ...       | 需 podaac-data-downloader, .netrc |
| OSCAR V2 FINAL/NRT  | OSCAR_V2_FINAL/OSCAR_V2_NRT| zonal_surface_current, ...    | 需 podaac-data-downloader, .netrc |
| SMAP L3 RSS FINAL   | SMAP_L3_RSS_FINAL         | surface_wind_speed            | 需 FTP 账号 |
| SFMR HRD            | SFMR_HRD                  | surface_wind_speed, rain_rate | 公开/部分需 mission_id |

详细变量及参数请见各适配器源码。

## 缓存机制

- 所有下载的原始数据文件默认缓存于 `~/.spatiotemporal_data_cache` 目录。
- 若文件已存在则不会重复下载。
- 可手动清理该目录以释放空间。

## 依赖说明
- `xarray`, `pandas`, `requests`, `cdsapi`, `netCDF4`
- ERA5 需配置 `~/.cdsapirc`，详见 [CDS API 文档](https://cds.climate.copernicus.eu/api-how-to)
- PO.DAAC 需配置 `~/.netrc`，详见 [Earthdata Login](https://urs.earthdata.nasa.gov/)
- SMAP RSS 需申请 FTP 账号并设置环境变量 `RSS_FTP_USER` 和 `RSS_FTP_PASSWORD`
- SFMR 公开数据无需认证，部分需 mission_id

## 测试

```bash
pip install pytest
pytest spatiotemporal_data_library/test_spatiotemporal_data_library.py
```

## 贡献与反馈

欢迎 issue、PR 或邮件反馈改进建议。 