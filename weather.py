from datetime import datetime
import requests
import os
import sys
import json
import pytz
from linebot.models import (
    BubbleContainer, FlexSendMessage, TextSendMessage, TextMessage
)

weather_forecast_url = 'https://api.weatherbit.io/v2.0'

geocode_api_url = 'https://api.opencagedata.com/geocode/v1/json'
aqi_api_url = os.getenv('WEATHER_AQI_API', None)
weather_api_key = os.getenv('WEATHER_API_KEY', None)
geocode_api_key = os.getenv('GEOCODE_API_KEY', None)

if weather_api_key is None:
    print('Specify WEATHER_API_KEY in environment variable')
    sys.exit(1)

if geocode_api_key is None:
    print('Specify GEOCODE_API_KEY in environment variable')
    sys.exit(1)

if aqi_api_url is None:
    print('Specify WEATHER_AQI_API in environment variable')
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

    def get_weather_data(self, place_name_or_latlng):
        result = self._resolve_location_latlng(place_name_or_latlng)
        if len(result['results']) == 0:
            return "I couldn't find weather from your place or lat/lng: {}".format(place_name_or_latlng)
        geometry = result['results'][0]['geometry']
        weather_data = self.get_weather(geometry['lat'], geometry['lng'])
        weather_data['address'] = result['results'][0]
        return weather_data

    def get_weather_aqi(self):
        response = requests.get(aqi_api_url)
        return response.json()

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

    def get_weather_aqi_message(self):
        weather_aqi_data = self.get_weather_aqi()
        aqi_last = weather_aqi_data['AQILast']
        aqi_color_id = int(aqi_last['AQI']['color_id'])
        aqi_param = aqi_last['AQI']['param']
        img_logo_url = ''
        bg_color = '#FFFF00'
        aqi_level_text = 'Moderate'
        msg_text = ''
        aqi_description_text = 'PM 25 | 83 μg/m3'
        print('======= AQI color_id: {0} ======='.format(aqi_last['AQI']['color_id']))
        if aqi_color_id == 1:
            img_logo_url += 'https://i.imgur.com/35KrVow.png'
            bg_color = '#3bccff'
            aqi_level_text = 'Excellent'
            msg_text = 'คุณภาพอากาศดีมาก เหมาะสำหรับกิจกรรมกลางแจ้งและการท่องเที่ยว'
        elif aqi_color_id == 2:
            img_logo_url += 'https://i.imgur.com/CSa1YMU.png'
            bg_color = '#92d050'
            aqi_level_text = 'Good'
            msg_text = 'คุณภาพอากาศดี สามารถทำกิจกรรมกลางแจ้งและการท่องเที่ยวได้ตามปกติ'
        elif aqi_color_id == 3:
            img_logo_url += 'https://i.imgur.com/jaBgWYt.png'
            bg_color = '#ffff00'
            aqi_level_text = 'Moderate'
            msg_text = 'ประชาชนทั่วไป : สามารถทำกิจกรรมกลางแจ้งได้ตามปกติ\nผู้ที่ต้องดูแลสุขภาพเป็นพิเศษ : หากมีอาการเบื้องต้น เช่น ไอ หายใจลำบาก ระคายเคืองตา ควรลดระยะเวลาการทำกิจกรรมกลางแจ้ง'
        elif aqi_color_id == 4:
            img_logo_url += 'https://i.imgur.com/EZQO623.png'
            bg_color = '#ffa200'
            aqi_level_text = 'Unhealthy'
            msg_text = 'ประชาชนทั่วไป : ควรเฝ้าระวังสุขภาพ ถ้ามีอาการเบื้องต้น เช่น ไอ หายใจลำบาก ระคายเคืองตา ควรลดระยะเวลาการทำกิจกรรมกลางแจ้ง หรือใช้อุปกรณ์ป้องกันตนเองหากมีความจำเป็น\nผู้ที่ต้องดูแลสุขภาพเป็นพิเศษ : ควรลดระยะเวลาการทำกิจกรรมกลางแจ้ง หรือใช้อุปกรณ์ป้องกันตนเองหากมีความจำเป็น ถ้ามีอาการทางสุขภาพ เช่น ไอ หายใจลำบาก ตาอักเสบ แน่นหน้าอก ปวดศีรษะ หัวใจเต้นไม่เป็นปกติ คลื่นไส้ อ่อนเพลีย ควรปรึกษาแพทย์'
        elif aqi_color_id == 5: 
            img_logo_url += 'https://i.imgur.com/jJdrpp0.png'
            bg_color = '#ff3b3b'
            aqi_level_text = 'Very Unhealthy'
            msg_text = 'ทุกคนควรหลีกเลี่ยงกิจกรรมกลางแจ้งทั้งหมด หลีกเลี่ยงพื้นที่ที่มีมลพิษทางอากาศสูง หรือใช้อุปกรณ์ป้องกันตนเองหากมีความจำเป็น หากมีอาการทางสุขภาพควรปรึกษาแพทย์'
        if aqi_param == 'PM25':
            aqi_description_text = 'PM25 | {0} μg/m3'.format(aqi_last['PM25']['value'])
        elif aqi_param == 'PM10':
            aqi_description_text = 'PM10 | {0} μg/m3'.format(aqi_last['PM10']['value'])
        elif aqi_param == 'O3':
            aqi_description_text = 'O3 | {0} μg/m3'.format(aqi_last['O3']['value'])
        elif aqi_param == 'NO2':
            aqi_description_text = 'NO2 | {0} μg/m3'.format(aqi_last['NO2']['value'])
        elif aqi_param == 'SO2':
            aqi_description_text = 'SO2 | {0} μg/m3'.format(aqi_last['SO2']['value'])
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
                        "text": weather_aqi_data['nameEN'],
                        "align": "center",
                        "weight": "bold",
                        "color": "#FFFFFF"
                    },
                    {
                        "type": "text",
                        "text": weather_aqi_data['areaEN'],
                        "size": "xs",
                        "align": "center",
                        "color": "#FFFFFF",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": "{0} {1}".format(aqi_last['date'], aqi_last['time']),
                        "size": "xs",
                        "align": "center",
                        "color": "#FFFFFF"
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
                        "contents": [
                        {
                            "type": "image",
                            "url": img_logo_url,
                            "flex": 1,
                            "size": "4xl"
                        }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "flex": 1,
                        "contents": [
                        {
                            "type": "text",
                            "text": aqi_last['AQI']['aqi'],
                            "size": "4xl",
                            "align": "center",
                            "gravity": "top",
                            "wrap": True,
                            "weight": "bold",
                            "color": "#000000"
                        },
                        {
                            "type": "text",
                            "text": "US AQI ({0})".format(aqi_level_text),
                            "size": "xs",
                            "wrap": True,
                            "align": "center",
                            "color": "#000000"
                        },
                        {
                            "type": "text",
                            "text": aqi_description_text,
                            "wrap": True,
                            "size": "xs",
                            "align": "center",
                            "color": "#000000"
                        }
                        ]
                    }
                    ]
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
        messages = []
        flex_message = BubbleContainer.new_from_json_dict(bubble)
        print(json.dumps(bubble))
        messages.append(FlexSendMessage(alt_text='Air Quality Index', contents=flex_message))
        messages.append(TextSendMessage(text=msg_text))
        return messages
        
if __name__ == '__main__':
    # dt_str = '2018-09-08 10:49'
    # from_format = '%Y-%m-%d %H:%M'
    # to_format = '%a, %d %B %H:%M %p %z'
    # tz_str = 'Asia/Bangkok'
    # weather = Weather()
    # print(weather.convert_time(dt_str, tz_str, from_format, to_format))
    weather = Weather()
    print(weather.get_weather_aqi())
