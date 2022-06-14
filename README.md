# Forecast Parser

A container that parses forecast-files and provides access to them via an API.

## Description

This repo contains a python-script that will read/parse forecast files provided by DMI (Danmarks Meteorologiske Institut) (including relayed data from ECMWF) and ConWx. The data will be joined into a single pandas DataFrame and served via a REST API accepting SQL queries. The script is intended to be run as part of a container/kubernetes, so a Dockerfile is provided as well, as is a set of helm charts with a default configuration.

### Exposed environment variables:

| Name | Default value | Description |
|--|--|--|
|LOGLEVEL|"INFO"|Used to set log-level (set to DEBUG to show debug messages)|
|API_DBNAME|"weather_forecast"|Database name for use in the SQL query|
|API_PORT|5000|Port for accessing the API|
|USE_MOCK_DATA|"FALSE"|Set to true to generate mock-data (used for testing)|

More environment variables have been exposed, but will rarely be used. They can be found in the values.yaml file in the chart directory.

### File handling / Input

Every 10 seconds the '/app/weatherforecasts/' folder is scanned for new files. Files that fit given name-filters will be parsed one by one (and deleted) starting with the oldest first. The structure and contents of the files must fit the agreed structure (examples can be found in the '/tests/valid-testdata/' subfolder) and naming, otherwise the file will not be loaded. Be aware that any new valid forecast-file will overwrite old data of same forecast-type (i.e. a new ConWx file will overwrite the last ConWx forecast).

#### Using MOCK data

The container has an option to generate mock-data. This is done by taking the test-data files and changing their timestamps and dumping them into the input directory. This can be used if real forecast files are not available. The function will update timestamps and add new forecasts regularly, to simulate incoming data, but be aware that the forecast data itself will not change.

### API

The DataFrame is made available through a REST API which accepts SQL-queries. More information on the API itself can be found [here](https://github.com/energinet-singularity/singupy/tree/main/singupy#class-apidataframeapi).

The DataFrame contains the following columns/indexes:
| Name | type | description |
|--|--|--|
|lon|float|Longitude of measurement point|
|lat|float|Latitude of measurement point|
|time|datetime|UTC Timestamp of what time the forecast covers|
|calculation_time|datetime|UTC Timestamp of when the forecast was made|
|forecast_type|str|Name of the forecast type/source|
|temperature_2m|float|Temperature (K) at 2m|
|temperature_100m|float|Temperature (K) at 100m|
|wind_speed_10m|float|Wind speed (m/s) at 10m|
|wind_direction_10m|float|Wind direction (deg) at 10m|
|wind_speed_100m|float|Wind speed (m/s) at 100m|
|wind_direction_100m|float|Wind direction (deg) at 100m|
|direct_radiation|float|Short wave radiation (solar W/m2)|
|global_radiation|float|Short wave radiation per hour|
|global_radiation_ny|float|Short wave radiation per hour (extra)|
|accumulated_global_radiation|float|Accumulated daliy radiation (W/m2)|

## Getting Started

The quickest way to have something running is through docker (see the section [Running container](#running-container)).

Feel free to either import the python-file as a lib or run it directly - or use HELM to spin it up as a pod in kubernetes. These methods are not documented and you will need the know-how yourself (the files have been prep'ed to our best ability though).

### Dependencies

#### Python (if not run as part of the container)

The python script can probably run on any python 3.9+ version, but your best option will be to check the Dockerfile and use the same version as the container. Further requirements (python packages) can be found in the app/requirements.txt file.

#### Docker

Built and tested on version 20.10.12.

#### HELM (only relevant if using HELM for deployment)

Built and tested on version 3.7.0.

### Running container

1. Clone the repo to a suitable place
````bash
git clone https://github.com/energinet-singularity/forecast-parser.git
````

2. Build the container and create a volume
````bash
docker build forecast-parser/ -t forecast-parser:latest
docker volume create forecast-files
````

3. Start the container in docker
````bash
docker run -p 5000:5000 -v forecast-files:/app/weatherforecasts/ -it --rm forecast-parser:latest
````
The container will now be running interactively and you will be able to see the log output. To parse a forecast, it will have to be delivered to the volume somehow. This can be done by another container mapped to the same volume, or manually from another bash-client

To mock output data and show debugging information, use the two flags USE_MOCK_DATA and LOGLEVEL:
````bash
docker run -p 5000:5000 -e USE_MOCK_DATA=TRUE -e LOGLEVEL=DEBUG -v forecast-files:/app/weatherforecasts/ -it --rm forecast-parser:latest
````

Manual file-move to the volume (please verify volume-path is correct before trying this):
````bash
sudo cp forecast-parser/tests/valid-testdata/EnetEcm_2010010100.txt /var/lib/docker/volumes/forecast-files/_data/
````

4. To get some output from the dataframe, use postman, curl or the requests-package in python
````python
import requests
requests.post('http://localhost:5000/', json={"sql-query": 'SELECT * FROM weather_forecast LIMIT 5;'}).json()
````

NOTE: If using mock data, it will take some time before data will be available through the API - up to two hours, as data will
be dropped in the folder at "normal" times along the day.

## Help

Please submit an issue or ask the authors.

## Version History
* 2.0.0:
    * Drop kafka and kSQL implementation and switch to REST API.
    * Restructure code, introducing classes
    * Update Dockerfile and helm charts to newer "standard"
* 1.1.3:
    * First production-ready version
    <!---* See [commit change]() or See [release history]()--->

Older versions are not included in the README version history. For details on them, see the main-branch commit history, but beware: it was the early start and it was part of the learning curve, so it is not pretty. They are kept as to not disturb the integrity of the history.

## License

This project is licensed under the Apache-2.0 License - see the LICENSE.md file for details
