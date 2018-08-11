from datetime import datetime
import requests
import json
from linebot.models import (
    BubbleContainer
)

base_url = 'https://query.yahooapis.com/v1/public/yql'


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
                                        "text": "{0}, {1}".format(channel["location"]["city"], channel["location"]["country"]),
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
                                "text": "{0}º{1}".format(channel["item"]["condition"]["temp"], channel["units"]["temperature"]),
                                "size": "5xl",
                                "align": "center",
                                "action": {
                                    "type": "uri",
                                    "uri": channel["link"].split("*")[1]
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
        for index in range(1, 6):
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