import os
import sys
sys.path.append(os.path.join(os.path.split(os.path.split(__file__)[0])[0], "app"))

import parsers


def test_dmi_parser():
    test_file_path = os.path.join(os.path.split(__file__)[0], "valid-testdata")
    test_obj = {
        "Ecm": {
            "path": os.path.join(test_file_path, "EnetEcm_2010010100.txt"),
            "expected_cols": 12,
            "expected_rows": 28674,
            "lookup": [
                {
                    "col": "temperature_2m",
                    "row": 1000,
                    "value": 289.3
                },
                {
                    "col": "wind_speed_100m",
                    "row": 750,
                    "value": 11.2
                },
                ]
        },
        "NEA": {
            "path": os.path.join(test_file_path, "ENetNEA_2010010103.txt"),
            "expected_cols": 12,
            "expected_rows": 19470,
            "lookup": [
                {
                    "col": "temperature_2m",
                    "row": 1000,
                    "value": 289.8
                },
                {
                    "col": "wind_direction_100m",
                    "row": 5100,
                    "value": 31.0
                },
                ]
        }
    }
    helpers = parsers.get_dmi_helpers()

    for type in test_obj.values():
        with open(type["path"]) as file:
            file_contents = file.readlines()
        type["result"] = parsers.dmi_parser(file_contents, helpers)

    for type in test_obj.values():
        assert type["result"].shape == (type["expected_rows"], type["expected_cols"])
        for item in type["lookup"]:
            assert type["result"][item["col"]].iloc[item["row"]] == item["value"]


def test_conwx_parser():
    test_file_path = os.path.join(os.path.split(__file__)[0], "valid-testdata")
    test_obj = {
        "048": {
            "path": os.path.join(test_file_path, "ConWx_prog_2010010100_048.dat"),
            "expected_cols": 11,
            "expected_rows": 17346,
            "lookup": [
                {
                    "col": "temperature_2m",
                    "row": 1000,
                    "value": 289.42999999999995
                },
                {
                    "col": "wind_speed_100m",
                    "row": 750,
                    "value": 2.94
                },
                ]
        },
        "180": {
            "path": os.path.join(test_file_path, "ConWx_prog_2010010100_180.dat"),
            "expected_cols": 11,
            "expected_rows": 64074,
            "lookup": [
                {
                    "col": "temperature_2m",
                    "row": 1000,
                    "value": 281.63
                },
                {
                    "col": "wind_direction_100m",
                    "row": 5100,
                    "value": 264.74
                },
                ]
        }
    }
    app_path = os.path.join(os.path.split(os.path.split(__file__)[0])[0], "app")
    helpers = parsers.get_conwx_helpers(os.path.join(app_path, "gridpoints.csv"))

    for type in test_obj.values():
        with open(type["path"]) as file:
            file_contents = file.readlines()
        type["result"] = parsers.conwx_parser(file_contents, helpers)

    for type in test_obj.values():
        assert type["result"].shape == (type["expected_rows"], type["expected_cols"])
        for item in type["lookup"]:
            assert type["result"][item["col"]].iloc[item["row"]] == item["value"]
