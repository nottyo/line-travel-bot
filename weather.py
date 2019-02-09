from datetime import datetime
import requests
import os
import sys
import json
import pytz
import time
import dateutil.parser
from linebot.models import (
    BubbleContainer, FlexSendMessage, TextSendMessage, TextMessage, CarouselContainer
)

weather_forecast_url = 'https://api.weatherbit.io/v2.0'

geocode_api_url = 'https://api.opencagedata.com/geocode/v1/json'
aqi_api_token = os.getenv('WEATHER_AQI_API_TOKEN', None)
aqi_api_url = os.getenv('WEATHER_AQI_API', None)
weather_api_key = os.getenv('WEATHER_API_KEY', None)
geocode_api_key = os.getenv('GEOCODE_API_KEY', None)

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'

if weather_api_key is None:
    print('Specify WEATHER_API_KEY in environment variable')
    sys.exit(1)

if geocode_api_key is None:
    print('Specify GEOCODE_API_KEY in environment variable')
    sys.exit(1)

if aqi_api_url is None:
    print('Specify WEATHER_AQI_API in environment variable')
    sys.exit(1)

if aqi_api_token is None:
    print('Specify WEATHER_AQI_API_TOKEN in environment variable')
    sys.exit(1)


class Weather:

    # resolve location by lat lng or find lat,lng by location_name
    def _resolve_location_latlng(self, location_or_latlng):
        params = {
            'q': location_or_latlng,
            'abbrv': '1',
            'key': geocode_api_key
        }
        response = requests.get(geocode_api_url, params=params)
        return response.json()

    def get_current_weather(self, lat, lng):
        params = {
            'lat': lat,
            'lon': lng,
            'key': weather_api_key
        }
        response = requests.get(weather_forecast_url + '/current', params=params)
        return response.json()

    def get_weather_forecast_daily(self, lat, lng):
        params = {
            'lat': lat,
            'lon': lng,
            'key': weather_api_key
        }
        response = requests.get(weather_forecast_url + '/forecast/daily', params=params)
        return response.json()

    def get_weather(self, lat, lng):
        current_data = self.get_current_weather(lat, lng)
        daily_data = self.get_weather_forecast_daily(lat, lng)
        result = dict()
        result['current'] = current_data['data'][0]
        result['daily'] = daily_data['data']
        return result

    def get_latlng_from_place_name(self, place_name):
        result = self._resolve_location_latlng(place_name)
        if len(result['results']) == 0:
            return "I couldn't find weather from your place or lat/lng: {}".format(place_name)
        geometry = result['results'][0]['geometry']
        address = result['results'][0]
        return geometry, address

    def get_weather_data(self, place_name_or_latlng):
        geometry, address = self.get_latlng_from_place_name(place_name_or_latlng)
        weather_data = self.get_weather(geometry['lat'], geometry['lng'])
        weather_data['address'] = address
        return weather_data
    
    def get_weather_aqi_by_place_name(self, place_name):
        geometry = self.get_latlng_from_place_name(place_name_or_latlng)
        return self.get_weather_aqi(geometry['lat'], geometry['lng'])

    def get_weather_aqi(self, lat, lng):
        url = '{0}/feed/geo:{1};{2}/'.format(aqi_api_url, str(lat), str(lng))
        params = {
            'token': aqi_api_token
        }
        response = requests.get(url, params=params)
        return response.json()
    
    def _normalize_aqi_forecast_data(self, aqi_forecast_data):
        msg = aqi_forecast_data['rxs']['obs'][0]['msg']
        normalized_data = {
            'station_name': msg['i18n']['name']['en'],
            'station_link': msg['city']['url'],
            'aqi': msg['aqi'],
            'aqi_forecast': []
        }
        for af in msg['forecast']['aqi']:
            dt = dateutil.parser.parse(af['t'])
            date_str = dt.date().strftime('%Y-%m-%d')
            if not any(d['date'] == date_str for d in normalized_data['aqi_forecast']):
                  normalized_data['aqi_forecast'].append(
                      {
                          'date': date_str,
                          'min': af['v'][0],
                          'max': af['v'][1]
                      }
                  )
            else:
                for d in normalized_data['aqi_forecast']:
                    if d['date'] == date_str and af['v'][0] < d['min']:
                        d['min'] = af['v'][0]
                    if d['date'] == date_str and af['v'][1] > d['max']:
                        d['max'] = af['v'][1]
        return normalized_data
    
    def get_weather_aqi_forecast(self, station_id):
        url = '{0}/api/feed/@{1}/obs.en.json'.format(aqi_api_url, station_id)
        data = {
            'token': aqi_api_token,
            'uid': 'QKyXD1548496535374',
            'rqc': '2'
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': user_agent
        }
        response = requests.post(url, data=data, headers=headers)
        return response.json()
    
    def get_weather_aqi_daily_message(self, daily_data):
        flex_carousel = {
            "type": "carousel",
            "contents": []
        }
        for af in daily_data['aqi_forecast']:
            af['av'] = (af['max'] + af['min'])/2
            current_date = datetime.now().date().strftime('%Y-%m-%d')
            if af['date'] < current_date:
                continue
            if af['av'] > 0 and af['av'] <= 50:
                bg_color = '#009966'
                aqi_level_text = 'Good'
                text_color = '#ffffff'
            elif af['av'] > 50 and af['av'] <= 100:
                bg_color = '#ffde33'
                aqi_level_text = 'Moderate'
                text_color = '#000000'
            elif af['av'] > 100 and af['av'] <= 150:
                bg_color = '#ff9933'
                aqi_level_text = 'Unhealthy for Sensitive Groups'
                text_color = '#000000'
            elif af['av'] > 150 and af['av'] <= 200:
                bg_color = '#cc0033'
                aqi_level_text = 'Unhealthy'
                text_color = '#ffffff'
            elif af['av'] > 200 and af['av'] <= 300:
                bg_color = '#660099'
                aqi_level_text = 'Very Unhealthy'
                text_color = '#ffffff'
            elif af['av'] > 300:
                bg_color = '#7e0023'
                aqi_level_text = 'Hazardous'
                text_color = '#ffffff'
            bubble = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": self._format_date(af['date'], to_format='%a, %-d %b %Y'),
                            "size": "md",
                            "color": text_color,
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": daily_data['station_name'],
                            "size": "xs",
                            "color": text_color,
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": "{0} ~ {1}".format(af['min'], af['max']),
                            "size": "3xl",
                            "wrap": True,
                            "color": text_color,
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": aqi_level_text,
                            "wrap": True,
                            "color": text_color,
                            "size": "sm"
                        }
                    ]
                },
                "styles": {
                    "body": {
                    "backgroundColor": bg_color
                    }
                }
            }
            flex_carousel['contents'].append(bubble)
        carousel_msg = CarouselContainer.new_from_json_dict(flex_carousel)
        return FlexSendMessage(alt_text='AQI Daily Forecast', contents=carousel_msg)


    def _format_date(self, date_str, from_format="%Y-%m-%d", to_format="%a, %-d %b"):
        dt = datetime.strptime(date_str, from_format)
        return dt.strftime(to_format)

    # convert datetime from utc to local time
    def convert_time(self, dt_str, tz_str, from_format, to_format):
        dt = datetime.strptime(dt_str, from_format)
        local_tz = pytz.timezone(tz_str)
        dt = pytz.utc.localize(dt)
        return dt.astimezone(local_tz).strftime(to_format)

    def get_weather_message(self, weather_data):
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
                                        "text": "{0} {1}".format(weather_data["address"]["formatted"],
                                                                 weather_data["address"]["annotations"]["flag"]),
                                        "size": "sm",
                                        "wrap": True
                                    }
                                ]
                            },
                            {
                                "type": "text",
                                "text": self.convert_time(weather_data["current"]["ob_time"],
                                                          weather_data["current"]['timezone'],
                                                          '%Y-%m-%d %H:%M', '%a, %d %B %H:%M %p %z'),
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
                                "text": "{0}º".format(int(weather_data["current"]['temp'])),
                                "size": "5xl",
                                "align": "center",
                                "action": {
                                    "type": "postback",
                                    "data": "weather_hourly?lat={0}&lng={1}".format(
                                        weather_data["address"]["geometry"]["lat"],
                                        weather_data["address"]["geometry"][
                                            "lng"])
                                }
                            },
                            {
                                "type": "text",
                                "text": weather_data["current"]["weather"]["description"],
                                "weight": "bold",
                                "size": "lg",
                                "align": "center"
                            },
                            {
                                "type": "text",
                                "text": "{0}º / {1}º".format(int(weather_data["daily"][0]["min_temp"]),
                                                             int(weather_data["daily"][0]["max_temp"])),
                                "size": "sm",
                                "align": "center"
                            },
                            {
                                "type": "text",
                                "text": "Feels Like: {0}º".format(int(weather_data["current"]["app_temp"])),
                                "size": "xs",
                                "align": "center"
                            },
                            {
                                "type": "text",
                                "text": "Humidity: {0}%".format(weather_data["current"]["rh"]),
                                "size": "xs",
                                "align": "center"
                            },
                            {
                                "type": "text",
                                "text": "SunRise/Set: {0} / {1}".format(
                                    self.convert_time(weather_data["current"]["sunrise"],
                                                      weather_data["current"]['timezone'], '%H:%M', '%I:%M %p'),
                                    self.convert_time(weather_data["current"]["sunset"],
                                                      weather_data["current"]['timezone'], '%H:%M', '%I:%M %p')),
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
                        "spacing": "xs",
                        "contents": []
                    }
                ]
            }
        }
        bubble_forecast_contents = bubble["body"]["contents"][3]["contents"]
        for index in range(1, 6):
            data = weather_data["daily"][index]
            bubble_forecast_contents.append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "xs",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 4,
                            "contents": [
                                {
                                    "type": "text",
                                    "text": self._format_date(data["datetime"]),
                                    "size": "xs"
                                },
                                {
                                    "type": "text",
                                    "text": data["weather"]["description"],
                                    "size": "xxs"
                                }
                            ]
                        },
                        {
                            "type": "image",
                            "url": "https://www.weatherbit.io/static/img/icons/{0}.png".format(
                                data["weather"]["icon"]),
                            "size": "xxs",
                            "flex": 2
                        },
                        {
                            "type": "text",
                            "text": "{0}º/{1}º".format(int(data["min_temp"]), int(data["max_temp"])),
                            "size": "sm",
                            "align": "end",
                            "gravity": "center",
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
        response = requests.get(weather_forecast_url + '/forecast/hourly', params=params)
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
                            "text": "{0}º".format(int(data[index]['temp'])),
                            "gravity": "center",
                            "align": "center",
                            "flex": 2
                        },
                        {
                            "type": "text",
                            "size": "xs",
                            "text": "{0}º".format(int(data[index]['app_temp'])),
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

    
    def _check_aqi_level(self, aqi):
        aqi = int(aqi)
        result = {
            'level': '-1',
            'level_text': 'Unknown',
            'level_text_color': '#ffffff',
            'level_image': 'https://i.imgur.com/SD87jjB.png',
            'outdoor': {
                'image': 'https://i.imgur.com/IEwBqbv.png',
                'text': 'Unknown'
            },
            'mask': {
                'image': 'https://i.imgur.com/7vFN3AZ.png',
                'text': 'Unknown'
            }
        }
        if aqi >= 0 and aqi <= 50:
            # green
            result['level'] = '1'
            result['level_text'] = 'Good'
            result['level_text_color'] = '#1ABC9C'
            result['level_image'] = 'https://i.imgur.com/SD87jjB.png'
            result['outdoor']['text'] = 'No Risk'
            #'outdoor.image': 'https://i.imgur.com/krsW5US.png',
            result['mask']['text'] = 'Not Needed'
        elif aqi > 50 and aqi <= 100:
            # yellow
            result['level'] = '2'
            result['level_text'] = 'Moderate'
            result['level_text_color'] = '#f1c40f'
            result['level_image'] = 'https://i.imgur.com/vxX2nVF.png'
            result['outdoor']['text'] = 'People with respiratory disease should limit outdoor exertion'
            # 'outdor.image': 'https://i.imgur.com/uUQumwh.png',
            result['mask']['text'] = 'Recommended for People with respiratory disease'
        elif aqi > 100 and aqi <= 150:
            # orange
            result['level'] = '3'
            result['level_text'] = 'Unhealthy for Sensitive Groups'
            result['level_text_color'] = '#e67e22'
            # result['level_image'] = 'https://i.imgur.com/i5YnK6H.png'
            result['level_image'] = 'https://i.imgur.com/y7O7bvz.png'
            result['outdoor']['text'] = 'People with respiratory disease should limit outdoor exertion'
            #'outdoor.image': 'https://i.imgur.com/2MFtPg3.png',
            result['mask']['text'] = 'Recommended'
        elif aqi > 150 and aqi <= 200:
            # red
            result['level'] = '4'
            result['level_text'] = 'Unhealthy'
            result['level_text_color'] = '#e74c3c'
            result['level_image'] = 'https://i.imgur.com/DQE2DOJ.png'
            result['outdoor']['text'] = 'Everyone should limit outdoor exertion'
            # 'outdoor.image': 'https://i.imgur.com/m4Sve1v.png',
            result['mask']['text'] = 'Recommended'
        elif aqi > 200 and aqi < 300:
            # purple
            result['level'] = '5'
            result['level_text'] = 'Very Unhealthy'
            result['level_text_color'] = '#9b59b6'
            result['level_image'] = 'https://i.imgur.com/YHQoI3i.png'
            result['outdoor']['text'] = 'Everyone, esp children should limit outdoor exertion'
            # 'image': 'https://i.imgur.com/IZdDkkn.png',
            result['mask']['text'] = 'A Must'
        elif aqi >= 300:
            # dark red
            result['level'] = '6'
            result['level_text'] = 'Hazardous'
            result['level_text_color'] = '#902E46'
            result['level_image'] = 'https://i.imgur.com/VLAKdFj.png'
            result['outdoor']['text'] = 'Everyone should avoid all outdoor exertion'
            # 'outdoor.image': 'https://i.imgur.com/LFj1um8.png',
            result['mask']['text'] = 'A Must'
        return result

    def get_iaqi_by_param(self, iaqi_list, param_name):
        result = dict()
        result['current'] = '-'
        result['min'] = '-'
        result['max'] = '-'
        result['param'] = 'unknown'
        for data in iaqi_list:
            if data['p'] == param_name:
                result['param'] = data['p']
                result['current'] = data['v'][0]
                result['min'] = data['v'][1]
                result['max'] = data['v'][2]
        return result

    def _normalize_aqi_detail_data_v2(self, data):
        result = dict()
        msg = data['rxs']['obs'][0]['msg'] 
        result['station_name'] = msg['i18n']['name']['en']
        result['more_details_link'] = msg['city']['url']
        result['aqi'] = msg['aqi']
        result['level'] = self._check_aqi_level(result['aqi'])
        result['last_updated'] = 'Updated: {0}'.format(self._format_date(msg['time']['utc']['s'], 
                from_format='%Y-%m-%d %H:%M:%S', to_format='%a, %-d %b %Y %H:%M'))
        result['wind_speed'] = self.get_iaqi_by_param(msg['iaqi'] ,'w')
        result['pm25'] = self.get_iaqi_by_param(msg['iaqi'], 'pm25')
        return result
    
    def get_weather_aqi_message_v2(self, weather_aqi_data):
        data = weather_aqi_data['data']
        detail_data = self.get_weather_aqi_forecast(data['idx'])
        normalized_data = self._normalize_aqi_detail_data_v2(detail_data)
        normalized_data['idx'] = data['idx']
        bubble = {
            "type": "bubble",
            "direction": "ltr",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
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
                                        "text": normalized_data['station_name'],
                                        "size": "xs",
                                        "color": "#C1C4C5",
                                        "wrap": True
                                    }
                                ]
                            },
                            {
                                "type": "separator"
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "horizontal",
                                        "contents": [
                                            {
                                                "type": "image",
                                                "url": normalized_data['level']['level_image'],
                                                "size": "xs"
                                            },
                                            {
                                                "type": "text",
                                                "text": '{}'.format(normalized_data['aqi']),
                                                "size": "4xl",
                                                "gravity": "top",
                                                "color": normalized_data['level']['level_text_color']
                                            }
                                        ]
                                    },
                                    {
                                        "type": "text",
                                        "text": normalized_data['level']['level_text'],
                                        "align": "center",
                                        "color": normalized_data['level']['level_text_color']
                                    },
                                    {
                                        "type": "text",
                                        "text": normalized_data['last_updated'],
                                        "size": "xs",
                                        "align": "center",
                                        "color": "#C1C4C5"
                                    }
                                ]
                            },
                            {
                                "type": "separator"
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "md",
                                "contents": [
                                    {
                                        "type": "image",
                                        "url": "https://i.imgur.com/bHg8stH.png",
                                        "flex": 0,
                                        "align": "start",
                                        "gravity": "top",
                                        "size": "xxs"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "PM 2.5 (Today)",
                                                "size": "xs",
                                                "align": "start",
                                                "color": "#C1C4C5"
                                            },
                                            {
                                                "type": "text",
                                                "text": "{0} ~ {1} μg/m3".format(normalized_data['pm25']['min'], normalized_data['pm25']['max']),
                                                "size": "xs",
                                                "color": "#C1C4C5"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "separator"
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "md",
                                "contents": [
                                    {
                                        "type": "image",
                                        "url": "https://i.imgur.com/8Tb1qXF.png",
                                        "flex": 0,
                                        "align": "start",
                                        "gravity": "top",
                                        "size": "xxs"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "Wind Speed",
                                                "size": "xs",
                                                "align": "start",
                                                "color": "#C1C4C5"
                                            },
                                            {
                                                "type": "text",
                                                "text": "{0} m/s".format(normalized_data['wind_speed']['current']),
                                                "size": "xs",
                                                "color": "#C1C4C5"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "separator"
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "md",
                                "contents": [
                                    {
                                        "type": "image",
                                        # "url": "https://i.imgur.com/uUQumwh.png",
                                        # "url": "https://i.imgur.com/onXsTU2.png",
                                        "url": "https://i.imgur.com/p5oOfCK.png",
                                        "flex": 0,
                                        "align": "start",
                                        "gravity": "top",
                                        "size": "xxs"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "Outdoor Exertion",
                                                "size": "xs",
                                                "align": "start",
                                                "color": "#C1C4C5"
                                            },
                                            {
                                                "type": "text",
                                                "text": normalized_data['level']['outdoor']['text'],
                                                "size": "xs",
                                                "color": normalized_data['level']['level_text_color'],
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
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "md",
                                "contents": [
                                    {
                                        "type": "image",
                                        "url": "https://i.imgur.com/dpE8K8d.png",
                                        "flex": 0,
                                        "align": "start",
                                        "gravity": "top",
                                        "size": "xxs"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "Hygienic Mask",
                                                "size": "xs",
                                                "align": "start",
                                                "color": "#C1C4C5"
                                            },
                                            {
                                                "type": "text",
                                                "text": normalized_data['level']['mask']['text'],
                                                "size": "xs",
                                                "color": normalized_data['level']['level_text_color'],
                                                "wrap": True
                                            }
                                        ]
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
                        "layout": "vertical",
                        "spacing": "md",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "uri",
                                    "label": "More Details",
                                    "uri": normalized_data['more_details_link']
                                },
                                "color": normalized_data['level']['level_text_color'],
                                "style": "secondary"
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "postback",
                                    "label": "Daily Forecast",
                                    "text": "Daily Forecast",
                                    "data": "aqi_daily?station_id={0}".format(normalized_data['idx'])
                                },
                                "color": normalized_data['level']['level_text_color'],
                                "style": "secondary"
                            }
                        ]
                    }
                ]
            },
            "styles": {
                "body": {
                    "backgroundColor": "#033C5A"
                },
                "footer": {
                    "backgroundColor": "#033C5A"
                }
            }
        }
        flex_message = BubbleContainer.new_from_json_dict(bubble)
        return FlexSendMessage(alt_text='Air Quality Index', contents=flex_message)

    
    def get_weather_aqi_message(self, weather_aqi_data):
        data = weather_aqi_data['data']
        aqi_last = int(data['aqi'])
        aqi_level = 1
        bg_color = '#FFFF00'
        aqi_level_text = 'Moderate'
        msg_text = ''
        if aqi_last > 0 and aqi_last <= 50:
            bg_color = '#009966'
            aqi_level_text = 'Good'
            aqi_level = 1
            text_color = '#ffffff'
        elif aqi_last > 50 and aqi_last <= 100:
            bg_color = '#ffde33'
            aqi_level_text = 'Moderate'
            aqi_level = 2
            text_color = '#000000'
        elif aqi_last > 100 and aqi_last <= 150:
            bg_color = '#ff9933'
            aqi_level_text = 'Unhealthy for Sensitive Groups'
            aqi_level = 3
            text_color = '#000000'
        elif aqi_last > 150 and aqi_last <= 200:
            bg_color = '#cc0033'
            aqi_level_text = 'Unhealthy'
            aqi_level = 4
            text_color = '#ffffff'
        elif aqi_last > 200 and aqi_last <= 300:
            bg_color = '#660099'
            aqi_level_text = 'Very Unhealthy'
            aqi_level = 5
            text_color = '#ffffff'
        elif aqi_last > 300:
            bg_color = '#7e0023'
            aqi_level_text = 'Hazardous'
            aqi_level = 6
            text_color = '#ffffff'
        bubble = {
            "type": "bubble",
            "direction": "ltr",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "text",
                        "text": data['city']['name'],
                        "align": "center",
                        "size": "md",
                        "wrap": True,
                        "color": "#ffffff",
                        "action": {
                            "type": "uri",
                            "label": "AQI Description",
                            "uri": data['city']['url']
                        }
                    },
                    {
                        "type": "text",
                        "text": data['time']['s'],
                        "size": "xs",
                        "align": "center",
                        "color": "#ffffff",
                        "action": {
                            "type": "uri",
                            "label": "AQI Description",
                            "uri": data['city']['url']
                        }
                    },
                    {
                        "type": "text",
                        "text": 'Click me to see more detail',
                        "size": "xs",
                        "align": "center",
                        "color": "#ffffff"
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
                        "type": "box",
                        "layout": "vertical",
                        "flex": 1,
                        "contents": [
                        {
                            "type": "text",
                            "text": "Air Quality Index",
                            "size": "lg",
                            "align": "center",
                            "gravity": "top",
                            "wrap": True,
                            "weight": "bold",
                            "color": text_color
                        },
                        {
                            "type": "text",
                            "text": str(aqi_last),
                            "size": "5xl",
                            "align": "center",
                            "gravity": "top",
                            "wrap": True,
                            "weight": "bold",
                            "color": text_color
                        },
                        {
                            "type": "text",
                            "text": aqi_level_text,
                            "size": "lg",
                            "weight": "bold",
                            "wrap": True,
                            "align": "center",
                            "color": text_color
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
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "postback",
                            "label": "See Daily Forecast",
                            "data": "aqi_daily?station_id={0}".format(data['idx']),
                            "displayText": "AQI Daily Forecast"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "postback",
                            "label": "Cautionary Statement",
                            "data": "aqi_statement?level={0}".format(aqi_level),
                            "displayText": "Cautionary Statement for Air Pollution Level: \"{0}\"".format(aqi_level_text)
                        }
                    }
                ]
            },
            "styles": {
                "header": {
                    "backgroundColor": "#000000"
                },
                "body": {
                    "backgroundColor": bg_color
                }
            }
            }
        flex_message = BubbleContainer.new_from_json_dict(bubble)
        return FlexSendMessage(alt_text='Air Quality Index', contents=flex_message)
        
if __name__ == '__main__':
    # dt_str = '2018-09-08 10:49'
    # from_format = '%Y-%m-%d %H:%M'
    # to_format = '%a, %d %B %H:%M %p %z'
    # tz_str = 'Asia/Bangkok'
    # weather = Weather()
    # print(weather.convert_time(dt_str, tz_str, from_format, to_format))
    weather = Weather()
    print(weather.get_weather_aqi())
