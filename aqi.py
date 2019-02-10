
import requests
import os
import json
from datetime import datetime
import dateutil.parser
from dateutil.tz import gettz
api_host = os.getenv('NEW_AQI_API_HOST', None)
api_key = os.getenv('NEW_AQI_API_KEY', None)

from linebot.models import (
    BubbleContainer, FlexSendMessage, TextSendMessage, TextMessage, CarouselContainer
)

headers = {
    'user-agent': 'okhttp/3.12.0',
    'x-api-token': api_key,
    'x-user-lang': 'en_US',
    'Content-Type': 'application/json',
    'x-login-token': '', 
    'x-user-timezone': 'Asia/Bangkok',
    'x-aqi-index': 'us'
}

class WeatherAQI(object):

    def get_nearest_station(self, lat, lng):
        url = '{0}/api/v4/nearest'.format(api_host)
        req_body = {
            'lat': lat,
            'lon': lng
        }
        response = requests.post(url, headers=headers, json=req_body)
        resp_json = response.json()
        if resp_json['status'] == 'success':
            return resp_json['data']['id']
        return None
    
    def get_aqi_data(self, station_id):
        url = '{0}/api/v3/station/id?id={1}'.format(api_host, station_id)
        response = requests.get(url, headers=headers)
        resp_json = response.json()
        if resp_json['status'] == 'success':
            return resp_json['data']
        return None
    
    # custom text color, background color, icon
    def _get_aqi_message_style(self, aqi_level):
        styles = dict()
        if aqi_level > 0 and aqi_level <= 50:
            styles['text'] = 'Good'
            styles['background_color'] = '#a8e05f'
            styles['text_color'] = '#718B3C'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/3uysQp6.png'
            styles['level_image_url'] = 'https://i.imgur.com/nETuKgV.png'
                
        elif aqi_level > 50 and aqi_level <= 100:
            styles['text'] = 'Moderate'
            styles['background_color'] = '#FDD74B'
            styles['text_color'] = '#A57F23'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/jT8N7QZ.png'
            styles['level_image_url'] = 'https://i.imgur.com/S8flXXh.png'

        elif aqi_level > 100 and aqi_level <= 150:
            styles['text'] = 'Unhealthy for Sensitive Groups'
            styles['background_color'] = '#fe9b57'
            styles['text_color'] = '#b25826'
            styles['text_size'] = 'sm'
            styles['icon_url'] = 'https://i.imgur.com/ivh1pqK.png'
            styles['level_image_url'] = 'https://i.imgur.com/D0vyXVx.png'

        elif aqi_level > 150 and aqi_level <= 200:
            styles['text'] = 'Unhealthy'
            styles['background_color'] = '#fe6a69'
            styles['text_color'] = '#af2c3b'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/8tXR9wV.png'
            styles['level_image_url'] = 'https://i.imgur.com/Rbi6wIW.png'

        elif aqi_level > 200 and aqi_level <= 300:
            styles['text'] = 'Very Unhealthy'
            styles['background_color'] = '#A97ABE'
            styles['text_color'] = '#946AA9'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/rEfasQc.png'
            styles['level_image_url'] = 'https://i.imgur.com/eibuQO2.png'

        elif aqi_level > 300:
            styles['text'] = 'Hazardous'
            styles['background_color'] = '#7E4D51'
            styles['text_color'] = '#5D3B39'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/DhQWeMe.png'
            styles['level_image_url'] = 'https://i.imgur.com/qXm1PmD.png'
        return styles

    def get_aqi_message(self, aqi_raw_data):
        styles = self._get_aqi_message_style(aqi_raw_data['current_measurement']['aqius'])
        bubble = {
            "type": "bubble",
            "direction": "ltr",
            "header": {
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
                                "url": "https://i.imgur.com/m0st7TA.png",
                                "size": "xs"
                            },
                            {
                                "type": "text",
                                "text": "{0}, {1}".format(aqi_raw_data['name'], aqi_raw_data['city']),
                                "size": "xs",
                                "align": "start",
                                "color": "#C1C4C5",
                                "wrap": True
                            }
                        ]
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "image",
                                "url": styles['icon_url'],
                                "flex": 0
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": str(aqi_raw_data['current_measurement']['aqius']),
                                        "size": "xxl",
                                        "align": "center",
                                        "weight": "bold",
                                        "color": styles['text_color']
                                    },
                                    {
                                        "type": "text",
                                        "text": "US AQI",
                                        "size": "xs",
                                        "align": "center",
                                        "color": styles['text_color']
                                    },
                                    {
                                        "type": "text",
                                        "text": styles['text'],
                                        "size": styles['text_size'],
                                        "align": "center",
                                        "gravity": "center",
                                        "weight": "bold",
                                        "color": styles['text_color'],
                                        "wrap": True
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "image",
                                        "url": "https://airvisual.com/images/{0}.png".format(aqi_raw_data['current_weather']['ic']),
                                        "flex": 0,
                                        "size": "xxs"
                                    },
                                    {
                                        "type": "text",
                                        "text": "{0} °".format(aqi_raw_data['current_weather']['tp']),
                                        "size": "md",
                                        "gravity": "center",
                                        "color": "#AAAAAA"
                                    }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "image",
                                        "url": "https://i.imgur.com/e8ZIslf.png",
                                        "flex": 0,
                                        "size": "xxs"
                                    },
                                    {
                                        "type": "text",
                                        "text": "{0}%".format(aqi_raw_data['current_weather']['hu']),
                                        "size": "md",
                                        "gravity": "center",
                                        "color": "#AAAAAA"
                                    }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "image",
                                        "url": "https://i.imgur.com/1qlbadb.png",
                                        "align": "start",
                                        "size": "xxs"
                                    },
                                    {
                                        "type": "text",
                                        "text": "{0} km/h".format(aqi_raw_data['current_weather']['ws']*3.6),
                                        "size": "sm",
                                        "gravity": "center",
                                        "color": "#AAAAAA",
                                        "wrap": True
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "type": "separator"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "Today Forecast",
                            "text": "Today Forecast",
                            "data": "aqi_today_forecast?station_id={0}".format(aqi_raw_data['_id'])
                        },
                        "color": "#D6D6D6",
                        "height": "sm",
                        "style": "secondary"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "Daily Forecast",
                            "text": "Daily Forecast",
                            "data": "aqi_daily_forecast?station_id={0}".format(aqi_raw_data['_id'])
                        },
                        "color": "#D6D6D6",
                        "height": "sm",
                        "style": "secondary"
                    }
                ]
            },
            "styles": {
                "header": {
                    "backgroundColor": "#033C5A"
                },
                "body": {
                    "backgroundColor": styles["background_color"]
                }
            }
        }
        return BubbleContainer.new_from_json_dict(bubble)

    def _convert_str_to_date(self, date_str, tz_str, output_date_format='%-I%p'):
        dt = dateutil.parser.parse(date_str)
        local_dt = dt.astimezone(gettz(tz_str))
        return local_dt.strftime(output_date_format)

    def get_aqi_today_message(self, aqi_raw_data, limit=7):
        local_timezone = aqi_raw_data['timezone']
        today_date_str = self._convert_str_to_date(aqi_raw_data['current_weather']['ts'], tz_str=local_timezone, output_date_format='%A %-d %B %Y')
        forecasts = aqi_raw_data['forecasts']
        bubble = {
            "type": "bubble",
            "direction": "ltr",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": today_date_str,
                        "align": "center",
                        "size": "sm"
                    },
                    {
                        "type": "separator"
                    }
                ]
            }
        }
        added_item = 0
        for index in range(0, limit):
            if added_item > limit:
                break
            timestamp = forecasts[index]['ts']
            if timestamp is not None: 
                bubble['body']['contents'].append(
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": self._convert_str_to_date(timestamp, tz_str=local_timezone),
                                "size": "sm",
                                "gravity": "center"
                            },
                            {
                                "type": "image",
                                "url": "https://airvisual.com/images/{0}.png".format(forecasts[index]['ic']),
                                "flex": 0,
                                "gravity": "center",
                                "size": "xs",
                                "aspectRatio": "2:1"
                            },
                            {
                                "type": "text",
                                "text": "{0} °C".format(forecasts[index]['tp']),
                                "size": "sm",
                                "gravity": "center"
                            },
                            {
                                "type": "image",
                                "url": self._get_aqi_message_style(forecasts[index]['aqius'])['level_image_url'],
                                "align": "end",
                                "gravity": "center",
                                "size": "xs",
                                "aspectRatio": "2:1"
                            }
                        ]
                    }
                )
                bubble['body']['contents'].append(
                    {
                        "type": "separator"
                    }
                )
                added_item += 1
        return BubbleContainer.new_from_json_dict(bubble)

    def get_aqi_daily_message(self, aqi_raw_data, limit=7):
        local_timezone = aqi_raw_data['timezone']
        daily_forecasts = aqi_raw_data['forecasts_daily']
        added_item = 0
        flex_carousel = {
            "type": "carousel",
            "contents": []
        }
        for index in range(0, limit):
            if added_item > limit:
                break
            bubble = {
                "type": "bubble",
                "direction": "ltr",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": []
                }
            }
            aqi = daily_forecasts[index]['aqius']
            styles = self._get_aqi_message_style(aqi)
            date_str = self._convert_str_to_date(daily_forecasts[index]['ts'], tz_str=local_timezone, output_date_format='%A %-d %B %Y')
            if date_str is not None:
                bubble['body']['contents'].extend(
                    [
                        {
                            "type": "text",
                            "text": date_str,
                            "size": "sm",
                            "align": "center",
                            "color": styles['text_color']
                        },
                        {
                            "type": "separator",
                            "color": styles['text_color']
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "image",
                                    "url": styles['icon_url'],
                                    "aspectRatio": "1:1",
                                    "flex": 0
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "{0}".format(aqi),
                                            "size": 'xxl',
                                            "align": "center",
                                            "weight": "bold",
                                            "color": styles['text_color']
                                        },
                                        {
                                            "type": "text",
                                            "text": "US AQI",
                                            "size": "xs",
                                            "align": "center",
                                            "color": styles['text_color']
                                        },
                                        {
                                            "type": "text",
                                            "text": styles['text'],
                                            "size": styles['text_size'],
                                            "align": "center",
                                            "gravity": "center",
                                            "weight": "bold",
                                            "color": styles['text_color'],
                                            "wrap": True
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                )
                bubble['styles'] = {
                    "body": {
                        "backgroundColor": styles['background_color']
                    }
                }
                added_item += 1
                bubble_container = BubbleContainer.new_from_json_dict(bubble)
                flex_carousel['contents'].append(bubble_container)
        carousel_container = CarouselContainer.new_from_json_dict(flex_carousel)
        return carousel_container