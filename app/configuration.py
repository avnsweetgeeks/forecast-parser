import logging
import os
from dataclasses import dataclass

log = logging.getLogger()


@dataclass
class Settings:
    LOGLEVEL: str = "INFO"
    API_DBNAME: str = "weather_forecast"
    API_PORT: int = 5000
    ECM_FILE_FILTER = r"EnetEcm_\d{10}\.txt"
    ECM_TYPE_NAME = "EnetEcm"
    NEA_FILE_FILTER = r"ENetNEA_\d{10}\.txt"
    NEA_TYPE_NAME = "ENetNEA"
    CONWX_FILE_FILTER = r"ConWx_prog_\d{10}_\d{3}\.dat"
    CONWX_TYPE_NAME = "ConWx"
    FORECAST_PATH: str = "/app/weatherforecasts/"
    TEMPLATE_PATH: str = "/app/"
    GRID_POINT_PATH: str = "app/gridpoints.csv"
    USE_MOCK_DATA: bool = False
    FOLDER_SCAN_INTERVAL_S: int = 10


def __load_settings_from_env(settings: Settings) -> Settings:
    try:
        if os.environ.get("LOGLEVEL").upper() == "DEBUG":
            enable_debug_log()

        attributes = [attr for attr in dir(settings) if not attr.startswith("_")]

        for attr in attributes:
            if os.environ.get(attr) is not None:
                if type(getattr(settings, attr)) == str:
                    setattr(settings, attr, os.environ.get(attr))
                elif type(getattr(settings, attr)) == int:
                    setattr(settings, attr, int(os.environ.get(attr)))
                elif type(getattr(settings, attr)) == bool:
                    if os.environ.get(attr).upper() in ["TRUE", "YES", "Y"]:
                        setattr(settings, attr, True)
                    elif os.environ.get(attr).upper() in ["FALSE", "NO", "N"]:
                        setattr(settings, attr, False)
                    else:
                        raise ValueError(
                            f"Environment variable '{attr}' is type bool, but has been set to '{os.environ.get(attr)}'"
                        )

            log.debug(f"Setting '{attr}' is set to '{getattr(settings, attr)}'")

    except Exception as e:
        log.exception(f"Loading settings failed with exception: {e}")
        raise e

    return settings


def get_settings(load_from_env: bool = True) -> Settings:
    settings = Settings
    if load_from_env:
        settings = __load_settings_from_env(settings=settings)
    return settings


def set_logging_format():
    logging.basicConfig(format="%(levelname)s:%(asctime)s:%(name)s - %(message)s")


def setup_log(app_log: logging.Logger, level: str):
    if hasattr(logging, level.upper()):
        app_log.setLevel(getattr(logging, level.upper()))
    else:
        raise KeyError(f"Trying to set loglevel to invalid value ({level}).")


def enable_debug_log():
    log.warning("Debug logging has been enabled!")
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)
