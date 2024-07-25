import datetime
import sys
import time
import logging
import requests
import json
import boto3
import botocore
import os

logging.getLogger().setLevel(logging.INFO)

OWMAPIURL = 'https://api.openweathermap.org'
dynamodb_table_name = os.environ['dynamodb_table_name']
region = os.environ['region']
ssm_client = boto3.client('ssm')
dynamodb_client = boto3.client('dynamodb')


'''Function that returns unix utc timestamps for the past 7 days. 
Timestamps are generated for the past 7 days every 2 hours.'''


def generate_datetimes(date_from_str=str(datetime.date.today() - datetime.timedelta(days=7)), days=7):
    dt_unix = list()
    date_from = datetime.datetime.strptime(date_from_str, '%Y-%m-%d')
    for hour in range(0, (24 * days), 2):
        dt_unix.append(int(time.mktime((date_from + datetime.timedelta(hours=hour)).timetuple())))
    return dt_unix


'''Function that returns latitude and longitude of New York City using OpenWeatherMap GeoCoding API.
API endpoint being used is http://api.openweathermap.org/geo/1.0/direct?q=New_York_City&appid={API key}'''


def get_lat_lon(api_key):
    nyc_lat_lon = dict()
    geo_api = OWMAPIURL + '/geo/1.0/direct?q=New_York_City&appid=' + api_key
    response = requests.get(geo_api)
    if response.status_code == 200:
        response_data = response.json()
        nyc_lat_lon['lat'] = str(response_data[0]['lat'])
        nyc_lat_lon['lon'] = str(response_data[0]['lon'])
        logging.info('New York latitude and longitude: {}'.format(nyc_lat_lon))
    else:
        logging.error(
            'Unable to fetch latitude and longitude for New York City, Error Code: {}'.format(response.status_code))
        sys.exit(1)
    return nyc_lat_lon


'''Function that returns dynamodb table item. Function throws exception if table does not exist'''


def get_dynamodb_item(time_id):
    try:
        dynamodb_item = dynamodb_client.get_item(
            Key={
                'TimeId': {
                    'S': time_id

                }
            },
            TableName=dynamodb_table_name,
        )
        if 'Item' in dynamodb_item:
            logging.info('Entry found in dynamodb for TimeId: {}'.format(time_id))
            return dynamodb_item['Item']
        else:
            return None
    except botocore.exceptions.ClientError as err:
        logging.error('Error Code: {}'.format(err.response['Error']['Code']))
        logging.error('Error Message: {}'.format(err.response['Error']['Message']))
        logging.error('Http Code: {}'.format(err.response['ResponseMetadata']['HTTPStatusCode']))
        logging.error('Request ID: {}'.format(err.response['ResponseMetadata']['RequestId']))
        sys.exit(1)


'''Function that writes item to dynamodb table.'''


def write_dynamodb_item(payload):
    dynamodb_payload = dict()
    for key, value in payload.items():
        dynamodb_payload[key] = {'S': str(value)}
    try:
        dynamodb_client.put_item(
            TableName=dynamodb_table_name,
            Item=dynamodb_payload)
    except botocore.exceptions.ClientError as err:
        logging.error('Error Code: {}'.format(err.response['Error']['Code']))
        logging.error('Error Message: {}'.format(err.response['Error']['Message']))
        logging.error('Http Code: {}'.format(err.response['ResponseMetadata']['HTTPStatusCode']))
        logging.error('Request ID: {}'.format(err.response['ResponseMetadata']['RequestId']))
        sys.exit(1)


'''Function that fetches current weather of New York City. API endpoint being used is 
https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API key}&units=metric'''


def get_current_weather(api_key):
    current_weather_doc = dict()
    # Get latitude and longitude New York City
    lat_lon = get_lat_lon(api_key)

    current_weather_api = OWMAPIURL + '/data/2.5/weather?units=metric&lat=' + lat_lon['lat'] + '&lon=' + lat_lon[
        'lon'] + '&appid=' + api_key
    logging.info("Getting current weather for New York City")

    # Query the OpenWeatherMap API to get current weather for New York City
    response = requests.get(current_weather_api)

    # Check the response code
    if response.status_code == 200:
        response_data = response.json()
        logging.info(response_data)

        # Build the current weather doc
        if 'name' in response_data:
            current_weather_doc['Name'] = response_data['name']
        if 'main' in response_data:
            if 'temp' in response_data['main']:
                current_weather_doc['Temperature(Celsius)'] = response_data['main']['temp']
            if 'humidity' in response_data['main']:
                current_weather_doc['Humidity(Percentage)'] = response_data['main']['humidity']
            if 'pressure' in response_data['main']:
                current_weather_doc['Pressure(hPa)'] = response_data['main']['pressure']
        if 'wind' in response_data:
            if 'speed' in response_data['wind']:
                current_weather_doc['Wind_Speed(m/sec)'] = response_data['wind']['speed']
        if 'weather' in response_data:
            if 'description' in response_data['weather'][0]:
                current_weather_doc['Description'] = response_data['weather'][0]['description']
        if 'dt' in response_data:
            current_weather_doc['weather_time'] = datetime.datetime.fromtimestamp(int(response_data['dt'])).strftime(
                '%Y-%m-%d %H:%M:%S')
        current_weather_doc['ingestion_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        '''Write the current weather document to dynamodb table. Primary Key: TimeId. 
        TimeId = str(current_unix_timestamp)_current'''
        write_dynamodb_item({'TimeId': str(datetime.datetime.now().strftime('%s')) + "_current"} | current_weather_doc)
        logging.info("Current Weather for New York City: {}".format(current_weather_doc))
        logging.info("Getting data for the past 7 days")

        # Get Historical Weather Data for  the past 7 days
        historical_weather = get_historical_weather(api_key)

        # Check if Average is returned in historical_weather
        if 'Average' in historical_weather['body']:
            current_weather_doc['Average'] = historical_weather['body']['Average']
            return {'statusCode': 200, 'body': json.dumps(current_weather_doc, indent=4)}
        else:
            return {'statusCode': 200, 'body': json.dumps(current_weather_doc, indent=4)}
    else:
        logging.error('Unable to fetch current weather for New York City, Error Code: {}'.format(response.status_code))
        return {'statusCode': response.status_code, 'body': json.dumps(
            'Unable to fetch current weather for New York City, Error Code: {}'.format(response.status_code))}


'''Function that fetches hitorical weather data of New York City for the past 7 days. API endpoint being used is 
https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={time}&appid={API key}&units=metric
'''


def get_historical_weather(api_key):
    historical_weather_data = dict()
    historical_weather_data['data'] = list()
    historical_weather_data['Average'] = dict()
    historical_average_data = dict()
    historical_average_data['Historical_Temperature(Celsius)'] = list()
    historical_average_data['Historical_Humidity(Percentage)'] = list()
    historical_average_data['Historical_Pressure(hPa)'] = list()
    historical_average_data['Historical_Wind_Speed(m/sec)'] = list()

    # Get latitude and longitude New York City
    lat_lon = get_lat_lon(api_key)

    datetimes = generate_datetimes()
    if not datetimes:
        logging.error('Unable to generate date times for the past 7 days')
        sys.exit(1)
    else:
        # Check if historical data exists in dynamodb for the past 7 days. If it does then return the data.
        dynamodb_it = get_dynamodb_item((str(datetimes[-1]) + '_avg'))
        if dynamodb_it is not None:
            response = dict()
            for key, value in dynamodb_it.items():
                if key != 'TimeId':
                    response[key] = value['S']
            return {'statusCode': 200, 'body': response}
        else:
            # Get historical weather data for the past 7 days.
            for date_time in datetimes:
                historical_weather_api = OWMAPIURL + '/data/3.0/onecall/timemachine?units=metric&lat=' + lat_lon[
                    'lat'] + '&lon=' + lat_lon['lon'] + '&appid=' + api_key + '&dt=' + str(date_time)
                logging.info('Getting historical weather for New York City, Date: {}'.format(
                    datetime.datetime.fromtimestamp(int(date_time)).strftime('%Y-%m-%d %H:%M:%S')))
                response = requests.get(historical_weather_api)
                if response.status_code == 200:
                    response_data = response.json()
                    # logging.info(response_data)
                    if 'data' in response_data:
                        historical_weather_data['data'].append(response_data['data'][0])
                        if 'temp' in response_data['data'][0]:
                            historical_average_data['Historical_Temperature(Celsius)'].append(
                                response_data['data'][0]['temp'])
                        if 'pressure' in response_data['data'][0]:
                            historical_average_data['Historical_Pressure(hPa)'].append(
                                response_data['data'][0]['pressure'])
                        if 'humidity' in response_data['data'][0]:
                            historical_average_data['Historical_Humidity(Percentage)'].append(
                                response_data['data'][0]['humidity'])
                        if 'wind_speed' in response_data['data'][0]:
                            historical_average_data['Historical_Wind_Speed(m/sec)'].append(
                                response_data['data'][0]['wind_speed'])
                else:
                    logging.error(
                        'Unable to fetch historical data for the past 7 days, Error Code: {}'.format(
                            response.status_code))
                    return {'statusCode': response.status_code, 'body':
                        {'Unable to fetch fetch historical data for the past 7 days, Error Code: {}'.format(
                            response.status_code)}}

    # Calculate Average Temperature, Pressure, Humidity and Wind Speed
    if not historical_average_data['Historical_Temperature(Celsius)']:
        logging.warning('No temperature data found for the past 7 days')
    else:
        historical_weather_data['Average']['Temperature_Average(Celsius)'] = sum(
            historical_average_data['Historical_Temperature(Celsius)']) / len(
            historical_average_data['Historical_Temperature(Celsius)'])
    if not historical_average_data['Historical_Pressure(hPa)']:
        logging.warning('No pressure data found for the past 7 days')
    else:
        historical_weather_data['Average']['Pressure_Average(hPa)'] = sum(
            historical_average_data['Historical_Pressure(hPa)']) / len(
            historical_average_data['Historical_Pressure(hPa)'])
    if not historical_average_data['Historical_Humidity(Percentage)']:
        logging.warning('No humidity data found for the past 7 days')
    else:
        historical_weather_data['Average']['Humidity_Average(Percentage)'] = sum(
            historical_average_data['Historical_Humidity(Percentage)']) / len(
            historical_average_data['Historical_Humidity(Percentage)'])
    if not historical_average_data['Historical_Wind_Speed(m/sec)']:
        logging.warning('No Wind speed data found for the past 7 days')
    else:
        historical_weather_data['Average']['Wind_Speed_Average(m/sec)'] = sum(
            historical_average_data['Historical_Wind_Speed(m/sec)']) / len(
            historical_average_data['Historical_Wind_Speed(m/sec)'])
    historical_weather_data['Average'] = json.dumps(historical_weather_data['Average'])

    write_payload = {'TimeId': (str(datetimes[-1]) + '_avg')} | historical_weather_data

    '''Write the current weather document to dynamodb table. Primary Key: TimeId. 
    TimeId = str(last_unix_timestamp_in_datetimes)_avg'''
    write_dynamodb_item(write_payload)

    return {'statusCode': 200, 'body': historical_weather_data}


def lambda_handler(event, context):
    try:
        # Get API Key from SSM
        api_key_ssm = ssm_client.get_parameter(Name='/owm/owmapikey', WithDecryption=True)
        api_key = api_key_ssm['Parameter']['Value']

        # Check the path in event.
        if event['rawPath'] == '/test/getWeatherNyc':
            return get_current_weather(api_key)
        else:
            return {'statusCode': 404, 'body': json.dumps('Not Found')}
    except Exception as e:
        logging.error(e, stack_info=True, exc_info=True)
        return {'statusCode': 500, 'body': json.dumps('Something went wrong')}
