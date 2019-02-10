
import requests
import os
import json
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
                
        elif aqi_level > 50 and aqi_level <= 100:
            styles['text'] = 'Moderate'
            styles['background_color'] = '#FDD74B'
            styles['text_color'] = '#A57F23'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/jT8N7QZ.png'

        elif aqi_level > 100 and aqi_level <= 150:
            styles['text'] = 'Unhealthy for Sensitive Groups'
            styles['background_color'] = '#fe9b57'
            styles['text_color'] = '#b25826'
            styles['text_size'] = 'sm'
            styles['icon_url'] = 'https://i.imgur.com/ivh1pqK.png'

        elif aqi_level > 150 and aqi_level <= 200:
            styles['text'] = 'Unhealthy'
            styles['background_color'] = '#fe6a69'
            styles['text_color'] = '#af2c3b'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/8tXR9wV.png'

        elif aqi_level > 200 and aqi_level <= 300:
            styles['text'] = 'Very Unhealthy'
            styles['background_color'] = '#A97ABE'
            styles['text_color'] = '#946AA9'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/rEfasQc.png'

        elif aqi_level > 300:
            styles['text'] = 'Hazardous'
            styles['background_color'] = '#7E4D51'
            styles['text_color'] = '#5D3B39'
            styles['text_size'] = 'xxl'
            styles['icon_url'] = 'https://i.imgur.com/DhQWeMe.png'
        return styles

    def get_aqi_message(self, aqi_raw_data):
        styles = self._get_aqi_message_style(aqi_raw_data['current_measurement']['aqius'])
        print(json.dumps(styles))
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
                "layout": "horizontal",
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
