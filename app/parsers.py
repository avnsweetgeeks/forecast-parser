import pandas as pd
import re
import logging
from datetime import timedelta as td

log = logging.getLogger()


def get_dmi_helpers() -> dict:
    """Creates a helper-dict for parsing DMI files

    The DMI files have headers that need to be translated into standard names
    in the DataFrame output. This function generates this mapping.

    Returns
    -------
    dict
        Dictionary containing 'column_map' for the dmi-parser
    """
    try:
        column_map = {
            "2m temperatur(K)": "temperature_2m",
            "10m wind speed(m/s)": "wind_speed_10m",
            "10m wind direction(deg)": "wind_direction_10m",
            "100m temperatur(K)": "temperature_100m",
            "100m wind speed(m/s)": "wind_speed_100m",
            "100m wind direction(deg)": "wind_direction_100m",
            "Accumulated short wave radiation (J/m2)": "accumulated_global_radiation",
            "Global radiation (W/m2)": "global_radiation",
            "Short wave radiation aka ny (W/m2)": "global_radiation_ny",
            "Short wave radiation per hour (W/m2)": "global_radiation",
        }

    except Exception as e:
        log.exception(e)
        raise e

    return {"column_map": column_map}


def get_conwx_helpers(geo_coordinate_file_path: str) -> dict:
    """Creates a helper-dict for parsing DMI files

    The DMI files have headers that need to be translated into standard names
    in the DataFrame output. This function generates this mapping.

    Parameters
    ----------
    geo_coordinate_file_path : str
        File containing geographical coordinate map for ConWx files

    Returns
    -------
    dict
        Dictionary containing 'column_map' and 'geo_coordinates' for ConWX
    """
    try:
        column_map = {
            "2 m temperature": "temperature_2m",
            "10 m wind speed": "wind_speed_10m",
            "10 m wind direction": "wind_direction_10m",
            "100 m temperature": "temperature_100m",
            "100 m wind speed": "wind_speed_100m",
            "100 m wind direction": "wind_direction_100m",
            "global radiation": "global_radiation",
        }

        geo_coordinates = {}
        with open(geo_coordinate_file_path) as file:
            for line in file.readlines()[1:]:
                geo_coordinates[int(line.split(",")[0])] = {
                    "lon": float(line.split(",")[1]),
                    "lat": float(line.split(",")[2]),
                }

    except Exception as e:
        log.exception(e)
        raise e

    return {"column_map": column_map, "geo_coordinates": geo_coordinates}


def dmi_parser(file_contents: list[str], helpers: dict) -> pd.DataFrame:
    """Parse a DMI file and output a DataFrame

    Info about DMI format files:
    - First line contains forecast metadata
    - Lines starting with hash contain meta-data about following rows
      - They either contain a set of timestamps or a new parameter
    - Rows without a hash are data-rows

    Parameters
    ----------
    file_contents : list[str]
        The contents of a DMI-formatted forecast file
    helpers : dict
        Dictionary containing a 'column_map' of file parameters names and the
        column names they should be translated to in the DataFrame.

    Returns
    -------
    pd.DataFrame
        A DataFrame with three indexes - lon, lat and time (estimation time)
        and a column for each reading/measurement type.
    """
    try:
        DF_INDEX = ["lon", "lat", "time"]
        DT_FORMAT = "%Y%m%d%H"
        data_array = []
        df_out = pd.DataFrame({i: [] for i in DF_INDEX}).set_index(DF_INDEX)
        parameter = ""

        for line in file_contents[1:]:
            if line[0] == "#":
                if len(data_array) > 0:
                    df = (
                        pd.DataFrame(data_array)
                        .explode(["time", parameter])
                        .set_index(DF_INDEX)
                    )
                    df_out = df_out.join(df, how="outer")
                    data_array.clear()

                if "Valid times:" in line:
                    time_index = line[len("# Valid times: ") :].split()
                else:
                    try:
                        parameter = helpers["column_map"][
                            re.search(r" +(.+[a-z].+)", line).group(1)
                        ]
                    except Exception as e:
                        log.error(
                            "Could not translate column name - using 'INVALID_COL_NAME' in stead."
                        )
                        log.exception(e)
                        parameter = "INVALID_COL_NAME"
            else:
                data_array.append(
                    {
                        "lon": float(line.split()[0]),
                        "lat": float(line.split()[1]),
                        "time": pd.to_datetime(time_index, format=DT_FORMAT, utc=True),
                        parameter: [float(v) for v in line.split()[2:]],
                    }
                )

        df_out = df_out.join(
            pd.DataFrame(data_array).explode(["time", parameter]).set_index(DF_INDEX)
        )
        df_out["calculation_time"] = pd.to_datetime(
            re.search(r"Iteration = (\d+)", file_contents[0]).group(1),
            format=DT_FORMAT,
            utc=True,
        )
        df_out.fillna(0, inplace=True)

    except Exception as e:
        log.exception(e)
        raise e

    return df_out.reset_index()


def conwx_parser(file_contents: list[str], helpers: dict) -> pd.DataFrame:
    """Parse a ConWx file and output a DataFrame

    Info about ConWx format files:
    - First 13 lines contains forecast metadata/header info
    - Lines starting with hash contain a new parameter name for following rows
    - Rows without a hash are data-rows
    - First two columns are a coordinate set which can be looked up in file
      which is included in helper dict.
    - All lines containing "-99" values are outside requested area
    - Temperatures are in C - must be translated to K (add 273.15)

    Parameters
    ----------
    file_contents : list[str]
        The contents of a ConWx-formatted forecast file
    helpers : dict
        Dictionary containing a 'column_map' of file parameters names and the
        column names they should be translated to in the DataFrame and also a
        set of grid points they can be translated to.

    Returns
    -------
    pd.DataFrame
        A DataFrame with three indexes - lon, lat and time (estimation time)
        and a column for each reading/measurement type.
    """
    try:
        DF_INDEX = ["lon", "lat", "time"]
        DT_FORMAT = "%Y%m%d%H"
        data_array = []
        df_out = pd.DataFrame({i: [] for i in DF_INDEX}).set_index(DF_INDEX)
        parameter = ""

        calculation_time = pd.to_datetime(
            file_contents[0][len("#date=") :].rstrip(), format=DT_FORMAT, utc=True
        )
        forecast_horizon = int(file_contents[2][len("#maxlen=") :]) - int(
            file_contents[1][len("#minlen=") :]
        )
        time_index = [
            (calculation_time + td(hours=h)) for h in range(forecast_horizon + 1)
        ]

        for line in file_contents[13:]:
            if line[0] == "#":
                if len(data_array) > 0:
                    df = (
                        pd.DataFrame(data_array)
                        .explode(["time", parameter])
                        .set_index(DF_INDEX)
                    )
                    df_out = df_out.join(df, how="outer")
                    data_array.clear()

                parameter = helpers["column_map"][
                    re.search(r" +(.+[a-z].+)", line).group(1)
                ]
            else:
                if float(line.split()[4]) != -99:
                    grid_id = int(line.split()[0]) + (int(line.split()[1]) - 1) * 42
                    data_array.append(
                        {
                            "lon": helpers["geo_coordinates"][grid_id]["lon"],
                            "lat": helpers["geo_coordinates"][grid_id]["lat"],
                            "time": time_index,
                            parameter: [float(v) for v in line.split()[4:]],
                        }
                    )

        df_out = df_out.join(
            pd.DataFrame(data_array).explode(["time", parameter]).set_index(DF_INDEX)
        )
        df_out["calculation_time"] = calculation_time
        df_out["temperature_2m"] += 273.15
        df_out["temperature_100m"] += 273.15
        df_out.fillna(0, inplace=True)

    except Exception as e:
        log.exception(e)
        raise e

    return df_out.reset_index()
