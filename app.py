from flask import Flask, request, abort, jsonify
from weather import Weather
import os
import sys
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
    ImageMessage, VideoMessage, AudioMessage, FileMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent,
    FlexSendMessage, BubbleContainer, ImageComponent, BoxComponent,
    TextComponent, SpacerComponent, IconComponent, ButtonComponent,
    SeparatorComponent, CarouselContainer, QuickReply, QuickReplyButton, LocationAction
)

app = Flask(__name__)
weather = Weather()

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)


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


@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    weather_data = weather.get_weather_forecast(event.message.latitude, event.message.longitude)
    bubble_container = weather.get_weather_message(weather_data)
    line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Weather Forecast",
                                                                  contents=bubble_container))


@handler.add(PostbackEvent)
def handle_postback_event(event):
    data = event.postback.data
    if 'weather=' in data:
        weather_data = weather.get_weather_by_place(data.split("=")[1])
        bubble_container = weather.get_weather_message(weather_data)
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Weather Forecast",
                                                                      contents=bubble_container))


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text

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

    if 'weather in ' in text.lower():
        weather_data = weather.get_weather_by_place(text.split(" ")[2])
        if isinstance(weather_data, str):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=weather_data))
        else:
            bubble_container = weather.get_weather_message(weather_data)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Weather Forecast",
                                                                          contents=bubble_container))


if __name__ == '__main__':
    app.run(debug=True, port=5000)