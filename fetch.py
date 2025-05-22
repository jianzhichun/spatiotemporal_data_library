"""
Main entry point for spatiotemporal_data_library: fetch_data

This module provides a unified interface to fetch and standardize multi-source spatiotemporal Earth observation data, including ERA5, PO.DAAC (CYGNSS, OSCAR), SMAP RSS, and SFMR datasets.

Example:
    >>> from spatiotemporal_data_library import fetch_data
    >>> ds = fetch_data(
    ...     dataset_short_name="ECMWF_ERA5",
    ...     variables=["10m_u_component_of_wind", "10m_v_component_of_wind"],
    ...     start_time="2023-01-01T00:00:00Z",
    ...     end_time="2023-01-01T03:00:00Z",
    ...     bbox=[-5, 50, 0, 52]
    ... )
    >>> print(ds)
"""
import logging
import datetime
import xarray as xr
from typing import Union, List
from .adapters.era5 import ERA5Adapter
from .adapters.podaac import NOAACygnssL2Adapter, OSCARAdapter, PoDAACAdapterBase
from .adapters.smap_rss import SMAPRSSAdapter
from .adapters.sfmr import SFMRAdapter

# 数据集短名称常量
DS_NOAA_CYGNSS_L2 = "NOAA_CYGNSS_L2_V1.2"
DS_ECMWF_ERA5 = "ECMWF_ERA5"
DS_OSCAR_V2_FINAL = "OSCAR_V2_FINAL"
DS_OSCAR_V2_NRT = "OSCAR_V2_NRT"
DS_SMAP_L3_RSS_FINAL = "SMAP_L3_RSS_FINAL"
DS_SFMR_HRD = "SFMR_HRD"


def fetch_data(dataset_short_name: str,
               variables: List[str],
               start_time: Union[str, datetime.datetime],
               end_time: Union[str, datetime.datetime],
               bbox: List[float] = None,
               point: List[float] = None,
               **kwargs) -> xr.Dataset:
    """
    Fetch spatiotemporal data from a specified dataset and return a standardized xarray.Dataset.

    Supports ERA5, PO.DAAC (CYGNSS, OSCAR), SMAP RSS, SFMR, etc. via a unified interface.

    Args:
        dataset_short_name (str): Short name of the dataset (e.g., "ECMWF_ERA5", "NOAA_CYGNSS_L2_V1.2").
        variables (list[str]): List of standardized variable names to fetch.
        start_time (str or datetime.datetime): Start time (ISO string or datetime object).
        end_time (str or datetime.datetime): End time (ISO string or datetime object).
        bbox (list[float], optional): Geographic bounding box [min_lon, min_lat, max_lon, max_lat].
        point (list[float], optional): Single point [lon, lat].
        **kwargs: Adapter-specific parameters (e.g., pressure_level, storm_name, mission_id, etc.).

    Returns:
        xarray.Dataset: Standardized dataset containing the requested variables and coordinates.

    Raises:
        ValueError: If the dataset_short_name is not supported.
        Exception: For any errors during data fetching or processing.

    Example:
        >>> ds = fetch_data(
        ...     dataset_short_name="ECMWF_ERA5",
        ...     variables=["10m_u_component_of_wind", "10m_v_component_of_wind"],
        ...     start_time="2023-01-01T00:00:00Z",
        ...     end_time="2023-01-01T03:00:00Z",
        ...     bbox=[-5, 50, 0, 52]
        ... )
        >>> print(ds)
    """
    logging.info(f"正在为 {dataset_short_name} 获取变量 {variables} 的数据")

    adapter_class = None
    adapter_kwargs = kwargs.copy()

    if dataset_short_name == DS_NOAA_CYGNSS_L2:
        adapter_class = NOAACygnssL2Adapter
    elif dataset_short_name == DS_ECMWF_ERA5:
        adapter_class = ERA5Adapter
    elif dataset_short_name == DS_OSCAR_V2_FINAL or dataset_short_name == DS_OSCAR_V2_NRT:
        if dataset_short_name == DS_OSCAR_V2_NRT and 'oscar_product_type' not in adapter_kwargs:
            adapter_kwargs['oscar_product_type'] = 'nrt'
        elif dataset_short_name == DS_OSCAR_V2_FINAL and 'oscar_product_type' not in adapter_kwargs:
            adapter_kwargs['oscar_product_type'] = 'final'
        adapter_class = OSCARAdapter
    elif dataset_short_name == DS_SMAP_L3_RSS_FINAL:
        adapter_class = SMAPRSSAdapter
    elif dataset_short_name == DS_SFMR_HRD:
        adapter_class = SFMRAdapter
    else:
        raise ValueError(f"不支持的 dataset_short_name: {dataset_short_name}")

    adapter = adapter_class(dataset_short_name, variables, start_time, end_time, bbox, point, **adapter_kwargs)
    try:
        data = adapter.get_data()
        # 后处理：空间子集
        if point and data and data.sizes:
            logging.info(f"应用点选择: {point}")
            try:
                data = data.sel(latitude=point[1], longitude=point[0], method="nearest")
            except Exception as e:
                logging.warning(f"点选择时发生错误: {e}")
        elif bbox and data and data.sizes:
            is_bbox_handled_by_adapter = (dataset_short_name == DS_ECMWF_ERA5 or isinstance(adapter, PoDAACAdapterBase))
            if not is_bbox_handled_by_adapter:
                logging.info(f"应用边界框过滤器: {bbox}")
                try:
                    lat_coord_name = 'latitude' if 'latitude' in data.coords else 'lat' if 'lat' in data.coords else None
                    lon_coord_name = 'longitude' if 'longitude' in data.coords else 'lon' if 'lon' in data.coords else None
                    if lat_coord_name and lon_coord_name:
                        data = data.sel({lat_coord_name: slice(bbox[1], bbox[3]), lon_coord_name: slice(bbox[0], bbox[2])})
                    else:
                        logging.warning("无法应用 bbox 过滤器，因为在数据集中找不到纬度/经度坐标。")
                except Exception as e:
                    logging.warning(f"无法应用 bbox 过滤器: {e}")
        logging.info(f"已成功获取并处理 {dataset_short_name} 的数据。")
        return data
    except Exception as e:
        logging.error(f"获取 {dataset_short_name} 数据失败: {e}")
        raise
