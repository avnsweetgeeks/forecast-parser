import configuration
import parsers
import mock_data

import logging
import pandas as pd
import re
import os
import schedule
from singupy.api import DataFrameAPI as singuapi
from typing import Iterator, Callable
from time import sleep

log = logging.getLogger()


class WeatherForecast:
    type: str
    file_filter: str
    helpers: dict
    __df: pd.DataFrame = None
    __parser: Callable[[list[str], dict], pd.DataFrame]

    @property
    def df(self) -> pd.DataFrame:
        return self.__df

    def __init__(
        self,
        type: str,
        file_filter: str,
        parser: Callable[[list[str], dict], pd.DataFrame],
        helpers: dict = {},
    ) -> None:
        self.type = type
        self.file_filter = file_filter
        self.__parser = parser
        self.helpers = helpers

    def load(self, file_contents: list[str]) -> None:
        try:
            self.__df = self.__parser(file_contents, self.helpers)
        except Exception as e:
            log.error(f"Could not parse forecast - failed with error: {e}")


class ForecastManager:
    __forecasts: dict[WeatherForecast]
    __api: singuapi
    __dbname: str

    def __init__(self, api: singuapi, dbname: str) -> None:
        self.__forecasts = {}
        self.__api = api
        self.__dbname = dbname

    def __len__(self) -> int:
        return len(self.__forecasts)

    def __iter__(self) -> Iterator[WeatherForecast]:
        return iter(self.__forecasts.values())

    def __getitem__(self, name) -> WeatherForecast:
        try:
            return self.__forecasts[name]
        except Exception:
            log.error(
                f"Could not access WeatherForecast with name '{name}'"
                + " in ForecastJoiner object."
            )
            raise KeyError(f"Object contains no WeatherForecast with name '{name}'.")

    def __setitem__(self, name, forecast) -> None:
        if isinstance(forecast, WeatherForecast):
            self.__forecasts[name] = forecast
        elif forecast is None:
            if name in self.__forecasts:
                del self.__forecasts[name]
        else:
            log.error(
                f"Tried to set value of '{name}' WeatherForecast to an"
                + f" object of '{type(forecast)} type in ForecastJoiner object.'"
            )
            raise ValueError(
                "Input must be either a valid WeatherForecast object or 'None'"
            )

    def __delitem__(self, name) -> None:
        if name in self.__forecasts:
            del self.__forecasts[name]
        else:
            log.error(
                "Could not find (and thereby delete) WeatherForecast"
                + f" with name '{name}' in ForecastJoiner object."
            )
            raise KeyError(f"Object contains no WeatherForecast with name '{name}'.")

    @property
    def DataFrame(self) -> pd.DataFrame:
        try:
            return self.__api[self.__dbname]
        except Exception:
            return pd.DataFrame()

    def UpdateForecast(self):
        forecast_dict = [
            src.df.assign(forecast_type=src.type) for src in self.__forecasts.values() if src.df is not None
        ]
        self.__api[self.__dbname] = pd.concat(forecast_dict, ignore_index=True)

    def ScanPath(self, path: str):
        """Check for new files in path and update manager if relevant."""
        parse_list = {}

        for forecast in self.__forecasts.values():
            for file in list_files_by_age(path=path, filter=forecast.file_filter):
                parse_list[file] = forecast

        for file in parse_list:
            try:
                log.info(f"Parsing file '{file}' as type {parse_list[file].type}.")
                parse_list[file].load(load_file(file))
            except Exception as e:
                log.error(f"Could not load forecast in file '{file}'.")
                log.exception(e)

        if len(parse_list) > 0:
            self.UpdateForecast()


def list_files_by_age(path: str, filter: str = ".*") -> list[str]:
    """List files in 'path' where file name fits 'filter' and sort with oldest first"""
    file_list = []

    try:
        file_list = [
            file.path
            for file in os.scandir(path)
            if file.is_file() and re.match(filter, file.name)
        ]
        file_list.sort(key=os.path.getmtime)

    except Exception:
        log.exception(f"An exception occurred while listing files in path '{path}'")
        # TODO : raise exception when running as sidecar or file handling inside container

    return file_list


def load_file(file_path: str, remove_file_after_load: bool = True) -> list[str]:
    """Load file 'file_path' into list and remove it if 'remove_file_after_load'"""
    try:
        file_contents = []
        with open(file_path) as file:
            file_contents = file.readlines()
    except Exception:
        log.error(f"Could not read file: '{file_path}'.")

    if remove_file_after_load:
        try:
            os.remove(file_path)
        except Exception:
            log.error(f"Could not remove file: '{file_path}'")

    return file_contents


def get_manager(settings: configuration.Settings) -> ForecastManager:
    forecast_api = singuapi(dbname=settings.API_DBNAME, port=settings.API_PORT)
    forecast_manager = ForecastManager(api=forecast_api, dbname=settings.API_DBNAME)

    forecast_manager[settings.ECM_TYPE_NAME] = WeatherForecast(
        type=settings.ECM_TYPE_NAME,
        file_filter=settings.ECM_FILE_FILTER,
        parser=parsers.dmi_parser,
        helpers=parsers.get_dmi_helpers(),
    )

    forecast_manager[settings.NEA_TYPE_NAME] = WeatherForecast(
        type=settings.NEA_TYPE_NAME,
        file_filter=settings.NEA_FILE_FILTER,
        parser=parsers.dmi_parser,
        helpers=parsers.get_dmi_helpers(),
    )

    forecast_manager[settings.CONWX_TYPE_NAME] = WeatherForecast(
        type=settings.CONWX_TYPE_NAME,
        file_filter=settings.CONWX_FILE_FILTER,
        parser=parsers.conwx_parser,
        helpers=parsers.get_conwx_helpers(settings.GRID_POINT_PATH),
    )

    return forecast_manager


if __name__ == "__main__":
    configuration.set_logging_format()
    settings = configuration.get_settings()
    configuration.setup_log(log, settings.LOGLEVEL)
    log.info("Initializing forecast-parser..")

    if settings.USE_MOCK_DATA:
        log.info("Mock data enabled. Setting scheduler to run each hour at x:30.")
        schedule.every().hour.at(":30").do(
            mock_data.dummy_input_planner, template_path=settings.TEMPLATE_PATH, output_path=settings.FORECAST_PATH
        )

    forecast_manager = get_manager(settings=settings)
    schedule.every(1).minutes.do(forecast_manager.ScanPath, path=settings.FORECAST_PATH)

    log.info("Initialization done - Starting scheduler..")
    while True:
        schedule.run_pending()
        sleep(settings.FOLDER_SCAN_INTERVAL_S)
