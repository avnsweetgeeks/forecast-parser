import logging
import os
import re
import time
from datetime import datetime as dt, timedelta as td

log = logging.getLogger()


def dummy_input_planner(template_path: str, output_path: str):
    """Take templates from 'template_path', update timestamps and output them to 'output_path'.

    Parameters
    ----------
    template_path : str
        The path where the templates can be found.
    output_path : str
        The path where the mock data should be written to.
    """

    log.info("Running dummy-input generation")

    # Make template-file config
    CONFIG_DATA = {
        r"^ENetNEA_\d{10}\.txt$": {
            "filename": "ENetNEA_<timestamp>.txt",
            "delay_h": 3,
            "time_list": [1, 4, 7, 10, 13, 16, 19, 22],
        },
        r"^EnetEcm_\d{10}\.txt$": {
            "filename": "EnetEcm_<timestamp>.txt",
            "delay_h": 7,
            "time_list": [8, 20],
        },
        r"^ConWx_prog_\d{10}_048\.dat$": {
            "filename": "ConWx_prog_<timestamp>_048.dat",
            "delay_h": 5,
            "time_list": [0, 6, 12, 18],
        },
        r"^ConWx_prog_\d{10}_180\.dat$": {
            "filename": "ConWx_prog_<timestamp>_180.dat",
            "delay_h": 7,
            "time_list": [2, 8, 14, 20],
        },
    }

    # Go through all files in template path and check if they fit any of the config-regex
    for template_file in [
        fs_item for fs_item in os.scandir(template_path) if fs_item.is_file()
    ]:
        for config in [
            CONFIG_DATA[key]
            for key in CONFIG_DATA.keys()
            if re.search(key, template_file.name)
        ]:
            # Determine if the file is expected to arrive 'now'
            if dt.now().hour in config["time_list"]:
                new_timestamp = time.strftime(
                    r"%Y%m%d%H", (dt.now() - td(hours=config["delay_h"])).timetuple()
                )
                new_filename = config["filename"].replace("<timestamp>", new_timestamp)
                dummy_ouput_writer(template_file=template_file.path,
                                   output_file=os.path.join(output_path, new_filename),
                                   time_correction_h=config["delay_h"])


def dummy_ouput_writer(template_file: str, output_file: str, time_correction_h: int):
    try:
        with open(template_file) as f:
            template = f.read().split("\n")

        with open(output_file, "w") as f:
            f.write(
                "\n".join(
                    change_dummy_timestamp(
                        template, dt.now() - td(hours=time_correction_h)
                    )
                )
            )
        log.info(f"Created dummy-file '{output_file}'")
    except Exception as e:
        log.exception(e)
        raise e


def change_dummy_timestamp(
    contents: list[str], new_t0: dt = dt.now(), max_forecast_h: int = 1000
) -> list[str]:
    """Takes file contents (contents) as a list of lines and then changes the timestamp base on new_t0.

    Parameters
    ----------
    contents : list[str]
        Contents of the forecast-template.
    new_t0 : datetime.datetime
        (Optional) The new t0-timestamp.
        Default = now().
    max_forecast_h : int
        (Optional) Maximum hours - only used to somewhat verify regex value is a timestamp.
        Default = 1000 (leave alone if unsure)
    """
    # All templates have the t0 time at the end of first line after a '='-sign
    time_string = contents[0].replace(" ", "").split("=")[-1]
    template_t0 = dt.fromtimestamp(time.mktime(time.strptime(time_string, r"%Y%m%d%H")))

    new_contents = []
    for row in contents:
        new_row = row
        # Regex: Look for exactly 10 digits with no digits right before or after
        for match in re.finditer(r"(?<!\d)(\d{10})(?!\d)", row):
            try:
                template_time = dt.fromtimestamp(
                    time.mktime(time.strptime(match.group(0), r"%Y%m%d%H"))
                )
            except Exception:
                pass
            else:
                if (
                    0
                    <= (template_time - template_t0).total_seconds() / 3600
                    < max_forecast_h
                ):
                    new_time = new_t0 + (template_time - template_t0)
                    new_row = (
                        new_row[: match.start()]
                        + time.strftime(r"%Y%m%d%H", new_time.timetuple())
                        + new_row[match.end():]
                    )
        new_contents.append(new_row)

    return new_contents
