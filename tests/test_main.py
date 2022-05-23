from time import sleep
import pandas as pd
import os
import sys
sys.path.append(os.path.join(os.path.split(os.path.split(__file__)[0])[0], "app"))

import main


def test_list_files_by_age(tmpdir):
    # arrange
    testdir = tmpdir.mkdir("test-dir")

    for filename in ["A.txt", "C.txt", "DD.txt", "B.txt"]:
        testdir.join(filename).write("TEST")
        sleep(0.1)

    # act
    file_list = main.list_files_by_age(testdir.strpath, r"^\w\.txt$")
    filename_list = [os.path.split(filepath)[1] for filepath in file_list]

    # assert
    assert filename_list == ["A.txt", "C.txt", "B.txt"]


def test_load_file(tmpdir):
    testfile = os.path.join(tmpdir.mkdir("test-dir").strpath,  "test-input.txt")

    with open(testfile, "w") as f:
        f.write("this\nis\na\ntest\nfile\n")

    contents = main.load_file(testfile, False)
    assert len(contents) == 5
    assert contents[3] == "test\n"
    assert os.path.exists(testfile)

    contents = main.load_file(testfile)
    assert not os.path.exists(testfile)


def forecast_return(contents: list, helper: dict):
    df = pd.DataFrame({"test": [1, 2, 3], "contents": contents})
    df["dict"] = helper["dict"]
    return df


def test_class_WeatherForecast():
    forecast = main.WeatherForecast("XXX", "test-file", forecast_return, {"dict": [7, 8, 9]})
    forecast.load([4, 5, 6])

    expected = pd.DataFrame({"test": [1, 2, 3], "contents": [4, 5, 6], "dict": [7, 8, 9]})
    assert expected.equals(forecast.df)
    assert forecast.type == "XXX"
    assert forecast.file_filter == "test-file"
    assert forecast.helpers == {"dict": [7, 8, 9]}


def test_class_ForecastManager():
    manager = main.ForecastManager({}, "testname")
    w1 = main.WeatherForecast("W1", "YYY", forecast_return, {"dict": [7, 8, 9]})
    w1.load([4, 5, 6])
    w2 = main.WeatherForecast("W2", "BBB", forecast_return, {"dict": [17, 18, 19]})
    w2.load([14, 15, 16])

    manager["W1"] = w1
    manager["W2"] = w2
    assert manager.DataFrame.equals(pd.DataFrame())

    manager.UpdateForecast()

    expected = pd.DataFrame({
        "test": [1, 2, 3, 1, 2, 3],
        "contents": [4, 5, 6, 14, 15, 16],
        "dict": [7, 8, 9, 17, 18, 19],
        "forecast_type": ["W1", "W1", "W1", "W2", "W2", "W2"]})

    assert expected.equals(manager.DataFrame)
