from datetime import datetime
import requests
import os
import sys
import json
from linebot.models import (
    BubbleContainer
)

base_url = 'https://query.yahooapis.com/v1/public/yql'
weather_forecast_hourly_url = 'https://api.weatherbit.io/v2.0/forecast/hourly'

weather_api_key = os.getenv('WEATHER_API_KEY', None)
if weather_api_key is None:
    print('Specify WEATHER_API_KEY in environment variable')
    sys.exit(1)


class Weather:

    def get_weather_forecast(self, lat, lng):
        yql = 'select * from weather.forecast where woeid in (select woeid from geo.places ' \
              'where text=\"({0}, {1})\") and u=\"c\"'.format(str(lat), str(lng))
        params = {
            'q': yql,
            'format': 'json'
        }
        response = requests.get(base_url, params=params)
        return response.json()

    def get_weather_by_place(self, place_name):
        yql = 'select * from weather.forecast where woeid in (select woeid from geo.places(1) ' \
              'where text=\"{0}\") and u=\"c\"'.format(str(place_name))
        params = {
            'q': yql,
            'format': 'json'
        }
        response = requests.get(base_url, params=params)
        resp_json = response.json()
        if resp_json['query']['results'] is None or 'item' not in resp_json["query"]["results"]["channel"]:
            return "I couldn't find weather from your place: {}".format(place_name)
        return response.json()

    def _format_date(self, date_str, from_format="%d %b %Y", to_format="%a, %d %b"):
        dt = datetime.strptime(date_str, from_format)
        return dt.strftime(to_format)

    def get_weather_message(self, weather_data):
        channel = weather_data["query"]["results"]["channel"]
        bubble = {
            "type": "bubble",
            "styles": {
                "body": {
                    "backgroundColor": "#ffffff"
                }
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "icon",
                                        "url": "https://static.thenounproject.com/png/14236-200.png"
                                    },
                                    {
                                        "type": "text",
                                        "text": "{0}, {1}".format(channel["location"]["city"],
                                                                  channel["location"]["country"]),
                                        "size": "sm"
                                    }
                                ]
                            },
                            {
                                "type": "text",
                                "text": channel["lastBuildDate"],
                                "size": "xxs"
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xs",
                        "contents": [
                            {
                                "type": "text",
                                "text": "{0}º{1}".format(channel["item"]["condition"]["temp"],
                                                         channel["units"]["temperature"]),
                                "size": "5xl",
                                "align": "center",
                                "action": {
                                    "type": "postback",
                                    "data": "weather_hourly?lat={0}&lng={1}".format(channel["item"]["lat"],
                                                                                    channel["item"]["long"])
                                }
                            },
                            {
                                "type": "text",
                                "text": channel["item"]["condition"]["text"],
                                "weight": "bold",
                                "size": "sm",
                                "align": "center"
                            },
                            {
                                "type": "text",
                                "text": "{0}º{1} / {2}º{3}".format(channel["item"]["forecast"][0]["low"],
                                                                   channel["units"]["temperature"],
                                                                   channel["item"]["forecast"][0]["high"],
                                                                   channel["units"]["temperature"]),
                                "size": "sm",
                                "align": "center"
                            },
                            {
                                "type": "text",
                                "text": "Wind: {0} {1}".format(channel["wind"]["speed"], channel["units"]["speed"]),
                                "size": "xs",
                                "align": "center"
                            },
                            {
                                "type": "text",
                                "text": "Humidity: {0}%".format(channel["atmosphere"]["humidity"]),
                                "size": "xs",
                                "align": "center"
                            },
                            {
                                "type": "text",
                                "text": "SunRise/Set: {0} / {1}".format(channel["astronomy"]["sunrise"],
                                                                        channel["astronomy"]["sunset"]),
                                "size": "xs",
                                "align": "center"
                            }
                        ]
                    },
                    {
                        "type": "separator"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "md",
                        "contents": []
                    }
                ]
            }
        }
        bubble_forecast_contents = bubble["body"]["contents"][3]["contents"]
        for index in range(1, 8):
            data = channel["item"]["forecast"][index]
            dt = self._format_date(data["date"])
            bubble_forecast_contents.append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": dt,
                            "size": "xxs",
                            "flex": 3
                        },
                        {
                            "type": "text",
                            "text": data["text"],
                            "size": "xxs",
                            "flex": 6
                        },
                        {
                            "type": "text",
                            "text": "{0}º/{1}º".format(data["low"], data["high"]),
                            "size": "xxs",
                            "flex": 2
                        }
                    ]
                }
            )
            bubble_forecast_contents.append(
                {
                    "type": "separator"
                }
            )
        return BubbleContainer.new_from_json_dict(bubble)

    def get_weather_forcast_hourly(self, lat, lng):
        params = {
            'lat': lat,
            'lon': lng,
            'key': weather_api_key
        }
        response = requests.get(weather_forecast_hourly_url, params=params)
        return response.json()

    def get_weather_forecast_hourly_data(self, hourly_data, limit=10):
        date = self._format_date(hourly_data['data'][0]['timestamp_local'], '%Y-%m-%dT%H:%M:%S', '%a, %-d %B %Y')
        data = hourly_data['data']
        bubble = {
            "type": "bubble",
            "styles": {
                "body": {
                    "backgroundColor": "#ffffff"
                }
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "md",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "icon",
                                        "url": "https://static.thenounproject.com/png/14236-200.png"
                                    },
                                    {
                                        "type": "text",
                                        "text": "{0}, {1}".format(hourly_data['city_name'],
                                                                  hourly_data['country_code']),
                                        "size": "lg"
                                    }
                                ]
                            },
                            {
                                "type": "text",
                                "text": date,
                                "size": "xs"
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "size": "xxs",
                                "text": "Time",
                                "flex": 8
                            },
                            {
                                "type": "text",
                                "size": "xxs",
                                "text": "Temp",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "size": "xxs",
                                "text": "Feels Like",
                                "flex": 3
                            }
                        ]
                    },
                    {
                        "type": "separator"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "xs",
                        "contents": []
                    }
                ]
            }
        }
        bubble_body_contents = bubble['body']['contents'][3]['contents']
        for index in range(0, limit):
            bubble_body_contents.append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 5,
                            "contents": [
                                {
                                    "type": "text",
                                    "size": "xxs",
                                    "weight": "bold",
                                    "text": self._format_date(data[index]['timestamp_local'],
                                                              '%Y-%m-%dT%H:%M:%S', '%-I%p')
                                },
                                {
                                    "type": "text",
                                    "size": "xxs",
                                    "wrap": True,
                                    "text": data[index]['weather']['description']
                                }
                            ]
                        },
                        {
                            "type": "image",
                            "url": "https://www.weatherbit.io/static/img/icons/{0}.png".format(
                                data[index]['weather']['icon']),
                            "size": "xxs",
                            "flex": 3
                        },
                        {
                            "type": "text",
                            "size": "xs",
                            "text": "{0}º".format(data[index]['temp']),
                            "gravity": "center",
                            "align": "center",
                            "flex": 2
                        },
                        {
                            "type": "text",
                            "size": "xs",
                            "text": "{0}º".format(data[index]['app_temp']),
                            "gravity": "center",
                            "align": "center",
                            "flex": 3
                        }
                    ]
                }
            )
            bubble_body_contents.append(
                {
                    "type": "separator"
                }
            )
        return BubbleContainer.new_from_json_dict(bubble)
