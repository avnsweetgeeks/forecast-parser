import shutil
import requests
import os
import sys
sys.path.append(os.path.join(os.path.split(os.path.split(__file__)[0])[0], "app"))

import main
import configuration


def test_endtoend(tmpdir):
    test_dir = tmpdir.mkdir("forecast-input").strpath
    settings = configuration.get_settings(load_from_env=False)
    for file in os.scandir(os.path.join(os.path.split(__file__)[0], "valid-testdata")):
        if "_048" not in file.name:
            shutil.copy(file.path, os.path.join(test_dir, file.name))

    forecast_manager = main.get_manager(settings=settings)
    forecast_manager.ScanPath(test_dir)

    assert len(forecast_manager.DataFrame) == 112218
    assert len(forecast_manager.DataFrame.columns) == 14

    print(forecast_manager.DataFrame)

    query = 'SELECT * FROM weather_forecast WHERE wind_speed_100m = 2.7'
    query += ' AND wind_direction_100m = 92;'

    test_data = requests.post('http://localhost:5000/', json={"sql-query": query}).json()

    assert test_data["lon"]["0"] == 10.0551
    assert test_data["lat"]["0"] == 55.2323
    assert test_data["forecast_type"]["0"] == "EnetEcm"

    query = 'SELECT * FROM weather_forecast WHERE lon = 10.5696793'
    query += ' AND lat = 56.6829834 AND wind_speed_100m = 12.17;'

    test_data = requests.post('http://localhost:5000/', json={"sql-query": query}).json()

    assert test_data["wind_direction_100m"]["0"] == 227.06
    assert test_data["wind_direction_10m"]["0"] == 219.37
    assert test_data["forecast_type"]["0"] == "ConWx"
