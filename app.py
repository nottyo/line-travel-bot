# -*- coding: utf-8 -*-

from flask import Flask, request, abort, jsonify, send_from_directory
from weather import Weather
from places import Places
from flight_api import FlightApi
import os
import sys
import json
import re
import errno
import requests
from linebot import (
    LineBotApi, WebhookHandler
)

from linebot.exceptions import (
    LineBotApiError, InvalidSignatureError
)

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageAction,
    ButtonsTemplate, ImageCarouselTemplate, ImageCarouselColumn, URIAction,
    PostbackAction, DatetimePickerAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage, FileMessage, ImageSendMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent,
    FlexSendMessage, BubbleContainer, ImageComponent, BoxComponent,
    TextComponent, SpacerComponent, IconComponent, ButtonComponent,
    SeparatorComponent, CarouselContainer, QuickReply, QuickReplyButton, LocationAction, CameraAction,
    CameraRollAction
)

app = Flask(__name__)
weather = Weather()
places = Places()
flight_api = FlightApi()
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)


def make_static_tmp_dir():
    try:
        print("Create Static Dir: " + static_tmp_path)
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        print("Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            print("  %s: %s" % (m.property, m.message))
        print("\n")
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@app.route("/", methods=['GET'])
def health_check():
    return jsonify(
        {
            'status': 'UP'
        }
    )

@app.route('/aqi', methods=['GET'])
def push_aqi():
    to = request.args.get('id')
    print('====== PUSH AQI TO: {} ======='.format(to))
    messages = weather.get_weather_aqi_message()
    line_bot_api.push_message(to=to, messages=messages)
    return jsonify({
        'status': 'ok'
    })

def generate_flight_map(origin, destination, resolution='720x360'):
    url = 'http://www.gcmap.com/map'
    params = {
        'P': '{0}-{1}'.format(origin.upper(), destination.upper()),
        'MS': 'bm',
        'MR': '900',
        'MX': resolution,
        'PM': '*'
    }
    resp = requests.get(url, params=params)
    if resp.status_code == 200:
        dir_name = 'static'
        resolution = resolution.split('x')[1]
        filename = '{0}/{1}{2}_{3}.png'.format(dir_name, origin.upper(), destination.upper(), resolution)
        file_exist = os.path.exists(filename)
        if file_exist is False:
            with open(filename, 'wb') as f:
                for chunk in resp:
                    f.write(chunk)
        else: 
            print('====== FILE: {0} IS EXIST ========'.format(filename))
        return 'https://{0}/{1}'.format(request.host, filename)

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    latlng = '{0} {1}'.format(event.message.latitude, event.message.longitude)
    weather_data = weather.get_weather_data(latlng)
    bubble_container = weather.get_weather_message(weather_data)
    messages = []
    messages.append(FlexSendMessage(alt_text="Weather Forecast", contents=bubble_container))
    line_bot_api.reply_message(event.reply_token, messages=messages)


@handler.add(PostbackEvent)
def handle_postback_event(event):
    data = event.postback.data
    print('postback data:{}'.format(data))
    if 'place_search?' in data:
        query_params = data.split('?')[1]
        lat = float(query_params.split('&')[0].split('=')[1])
        lng = float(query_params.split('&')[1].split('=')[1])
        type = query_params.split('&')[2].split('=')[1]
        if type == 'all':
            places_data = places.get_nearby_places(lat, lng)
        else:
            places_data = places.get_nearby_places(lat, lng, type)
        messages = []
        if isinstance(places_data, str):
            messages.append(TextSendMessage(text=places_data))
            line_bot_api.reply_message(event.reply_token, messages=messages)
        else:
            messages.append(FlexSendMessage(alt_text='Places', contents=places_data))
            line_bot_api.reply_message(event.reply_token, messages)

    if 'weather=' in data:
        weather_data = weather.get_weather_data(data.split("=")[1])
        bubble_container = weather.get_weather_message(weather_data)
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Weather Forecast",
                                                                      contents=bubble_container))
    if 'weather_hourly?' in data:
        latlng = data.split('?')[1]
        lat, lng = latlng.split('&')
        lat = lat.split('=')[1]
        lng = lng.split('=')[1]
        forecast_hourly_data = weather.get_weather_forcast_hourly(lat, lng)
        bubble_container = weather.get_weather_forecast_hourly_data(forecast_hourly_data)
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Weather Forecast Hourly",
                                                                      contents=bubble_container))
    
    if 'flight_info' in data:
        flight_no = data.split('=')[1]
        latest_flight = flight_api.get_latest_flight(flight_no)
        if latest_flight is not None:
            flight_metadata = flight_api.get_flight_metadata(latest_flight['flight_number'], latest_flight['adshex'])
            if flight_metadata['success'] is True:
                flight_bubble = flight_api.create_flight_message(latest_flight['flight_number'], latest_flight['adshex'], flight_metadata['payload'])
                image_original_url = generate_flight_map(flight_metadata['payload']['flightData']['departureApt'], flight_metadata['payload']['flightData']['arrivalApt'])
                image_preview_url = generate_flight_map(flight_metadata['payload']['flightData']['departureApt'], flight_metadata['payload']['flightData']['arrivalApt'], '240x120')
                image_msg = ImageSendMessage(original_content_url=image_original_url, preview_image_url=image_preview_url)
                messages = []
                messages.append(FlexSendMessage(alt_text="Flight Information", contents=flight_bubble))
                messages.append(image_msg)
                line_bot_api.reply_message(event.reply_token, messages)

    if 'airport' in data:
        airport_code = data.split('=')[1]
        airport_name = flight_api.get_airport_name_from_code(airport_code)
        if airport_name is not None:
            airport_data = flight_api.get_airport_data(airport_code)
            if airport_data is not None:
                airport_message = flight_api.create_airport_message(airport_data)
                line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Airport Information",
                                                                            contents=airport_message))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Sorry, there is no airport information for \"{0}\"'.format(airport_name)))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Sorry, I could\'t find airport information for {0}'.format(airport_code)))
            

def print_source(event):
    if isinstance(event.source, SourceUser):
        print('user_id: {0}'.format(event.source.user_id))
    if isinstance(event.source, SourceRoom):
        print('room_id: {0}'.format(event.source.room_id))
    if isinstance(event.source, SourceGroup):
        print('group_id: {0}'.format(event.source.group_id))


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text
    print_source(event)
    if 'aqi' == text.lower():
        aqi_messages = weather.get_weather_aqi_message()
        line_bot_api.reply_message(event.reply_token, messages=aqi_messages)
    
    if 'มองบน' in text.lower():
        bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://media.giphy.com/media/5Wi5ydRYRM28q9Gvyv/giphy.gif",
                "size": "full",
                "aspectMode": "cover"
                }
        }
        bubble_container = BubbleContainer.new_from_json_dict(bubble)
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="มองบน", contents=bubble_container))

    if 'อากาศ' == text or 'weather' == text.lower():
        quick_reply = QuickReply(
            items=[
                QuickReplyButton(
                    action=LocationAction(label='Send Location')
                ),
                QuickReplyButton(
                    action=PostbackAction(label='Tokyo Weather', data='weather=tokyo', display_text='Tokyo Weather')
                ),
                QuickReplyButton(
                    action=PostbackAction(label='Seoul Weather', data='weather=seoul', display_text='Seoul Weather')
                ),
                QuickReplyButton(
                    action=PostbackAction(label='London Weather', data='weather=london',
                                          display_text='London Weather')
                )
            ]
        )
        reply_message = TextSendMessage(text="Let me know your location or place",
                                        quick_reply=quick_reply)
        line_bot_api.reply_message(event.reply_token, messages=reply_message)

    m = re.match('weather in (.*)', text.lower())

    if m is not None:
        place_name = m.group(1)
        weather_data = weather.get_weather_data(place_name)
        if isinstance(weather_data, str):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=weather_data))
        else:
            bubble_container = weather.get_weather_message(weather_data)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Weather Forecast",
                                                                          contents=bubble_container))

    n = re.match('flight (.*)', text.lower())
    if n is not None:
        latest_flight = flight_api.get_latest_flight(n.group(1).upper())
        if latest_flight is not None:
            flight_metadata = flight_api.get_flight_metadata(latest_flight['flight_number'], latest_flight['adshex'])
            if flight_metadata['success'] is True:
                flight_bubble = flight_api.create_flight_message(latest_flight['flight_number'], latest_flight['adshex'], flight_metadata['payload'])
                image_original_url = generate_flight_map(flight_metadata['payload']['flightData']['departureApt'], flight_metadata['payload']['flightData']['arrivalApt'])
                image_preview_url = generate_flight_map(flight_metadata['payload']['flightData']['departureApt'], flight_metadata['payload']['flightData']['arrivalApt'], '240x120')
                image_msg = ImageSendMessage(original_content_url=image_original_url, preview_image_url=image_preview_url)
                messages = []
                messages.append(FlexSendMessage(alt_text="Flight Information", contents=flight_bubble))
                messages.append(image_msg)
                line_bot_api.reply_message(event.reply_token, messages)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Sorry, I can\'t find your flight: {}. Please try another flight number'.format(n.group(1).upper())))

    p = re.match('(^[A-Z]{3}-[A-Z]{3}$)', text.upper())
    if p is not None:
        text = p.group(1).upper()
        origin = text.split('-')[0]
        destination = text.split('-')[1]
        flight_route_data = flight_api.get_flight_by_route(origin, destination)
        if flight_route_data is not None:
            carouesel_container = flight_api.create_flight_route_message(flight_route_data)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Flight {0} Route Info".format(text),
                                                                          contents=carouesel_container))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Sorry, There is no flight for "{}" route.'.format(text)))
    
    q = re.match('airport (.*)', text.lower())
    if q is not None:
        text = q.group(1).lower()
        airports = flight_api.get_airport_code(text)
        if airports is not None:
            quick_reply_items = []
            for airport in airports:
                airport_name = (airport['title'][:14] + ' ({0})'.format(airport['url'].split('/')[-1])) if len(airport['title']) > 14 else airport['title'] + ' ({0})'.format(airport['url'].split('/')[-1])
                quick_reply_items.append(
                    {
                        "type": "action",
                        "action": {
                            "type": "postback",
                            "label": airport_name,
                            "data": "airport={0}".format(airport['url'].split('/')[-1])
                        }
                    }
                )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Here are possible airports', quick_reply=QuickReply(items=quick_reply_items)))


make_static_tmp_dir()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)