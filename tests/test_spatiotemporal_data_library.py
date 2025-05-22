import pytest
import datetime
import xarray as xr
from spatiotemporal_data_library import fetch_data
from spatiotemporal_data_library.fetch import DS_ECMWF_ERA5, DS_OSCAR_V2_NRT, DS_NOAA_CYGNSS_L2, DS_SMAP_L3_RSS_FINAL, DS_SFMR_HRD

# 使用 pytest 的 monkeypatch 进行 mock

class DummyAdapter:
    def __init__(self, *args, **kwargs): pass
    def get_data(self):
        # 返回一个简单的 xarray.Dataset
        return xr.Dataset({'var': (('time',), [1, 2, 3])}, coords={'time': [0, 1, 2]})

def test_fetch_data_ecmwf_era5(monkeypatch):
    monkeypatch.setattr('spatiotemporal_data_library.fetch.ERA5Adapter', DummyAdapter)
    ds = fetch_data(
        dataset_short_name=DS_ECMWF_ERA5,
        variables=["10m_u_component_of_wind"],
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-01T01:00:00Z"
    )
    assert isinstance(ds, xr.Dataset)
    assert 'var' in ds

def test_fetch_data_oscar_nrt(monkeypatch):
    monkeypatch.setattr('spatiotemporal_data_library.fetch.OSCARAdapter', DummyAdapter)
    ds = fetch_data(
        dataset_short_name=DS_OSCAR_V2_NRT,
        variables=["zonal_surface_current"],
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-01T01:00:00Z"
    )
    assert isinstance(ds, xr.Dataset)

def test_fetch_data_noaa_cygnss(monkeypatch):
    monkeypatch.setattr('spatiotemporal_data_library.fetch.NOAACygnssL2Adapter', DummyAdapter)
    ds = fetch_data(
        dataset_short_name=DS_NOAA_CYGNSS_L2,
        variables=["surface_wind_speed"],
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-01T01:00:00Z"
    )
    assert isinstance(ds, xr.Dataset)

def test_fetch_data_smap_rss(monkeypatch):
    monkeypatch.setattr('spatiotemporal_data_library.fetch.SMAPRSSAdapter', DummyAdapter)
    ds = fetch_data(
        dataset_short_name=DS_SMAP_L3_RSS_FINAL,
        variables=["surface_wind_speed"],
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-01T01:00:00Z"
    )
    assert isinstance(ds, xr.Dataset)

def test_fetch_data_sfmr(monkeypatch):
    monkeypatch.setattr('spatiotemporal_data_library.fetch.SFMRAdapter', DummyAdapter)
    ds = fetch_data(
        dataset_short_name=DS_SFMR_HRD,
        variables=["surface_wind_speed"],
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-01T01:00:00Z",
        storm_name="DORIAN", year=2019, mission_id="20190828H1"
    )
    assert isinstance(ds, xr.Dataset)

def test_fetch_data_invalid_dataset():
    with pytest.raises(ValueError):
        fetch_data(
            dataset_short_name="INVALID_DATASET",
            variables=["var"],
            start_time="2023-01-01T00:00:00Z",
            end_time="2023-01-01T01:00:00Z"
        ) 