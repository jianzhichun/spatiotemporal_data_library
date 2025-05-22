import datetime
import xarray as xr
from abc import ABC, abstractmethod

class DataSourceAdapter(ABC):
    """
    数据源适配器的抽象基类。
    每个适配器处理一个特定的数据集。
    """
    def __init__(self, dataset_name, variables, start_time, end_time, bbox=None, point=None, **kwargs):
        self.dataset_name = dataset_name
        self.raw_variables_requested = variables
        self.start_time = self._parse_time(start_time)
        self.end_time = self._parse_time(end_time)
        self.bbox = bbox
        self.point = point
        self.kwargs = kwargs
        self.native_variables = self._map_variables(variables)

    def _parse_time(self, time_input):
        if isinstance(time_input, datetime.datetime):
            return time_input
        elif isinstance(time_input, str):
            try:
                if time_input.endswith("Z"):
                    time_input = time_input[:-1] + "+00:00"
                return datetime.datetime.fromisoformat(time_input)
            except ValueError:
                raise ValueError("无效的时间字符串格式。请使用 ISO 格式 (例如 YYYY-MM-DDTHH:MM:SSZ 或 YYYY-MM-DDTHH:MM:SS+00:00)。")
        else:
            raise TypeError("start_time 和 end_time 必须是 datetime 对象或 ISO 格式的字符串。")

    @abstractmethod
    def _map_variables(self, standardized_vars):
        pass

    @abstractmethod
    def _authenticate(self):
        pass

    @abstractmethod
    def _build_request_params(self):
        pass

    @abstractmethod
    def _fetch_raw_data(self, request_params):
        pass

    @abstractmethod
    def _parse_data(self, raw_data_path_or_content):
        pass

    @abstractmethod
    def _standardize_data(self, dataset: xr.Dataset) -> xr.Dataset:
        pass

    def get_data(self) -> xr.Dataset:
        self._authenticate()
        request_params = self._build_request_params()
        raw_data_info = self._fetch_raw_data(request_params)
        if not raw_data_info:
            return xr.Dataset()
        dataset = self._parse_data(raw_data_info)
        standardized_dataset = self._standardize_data(dataset)
        return standardized_dataset 