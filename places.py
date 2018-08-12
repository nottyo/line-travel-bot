import os
import sys
from datetime import datetime

import googlemaps
from flask import request
from linebot.models import (
    CarouselContainer, BubbleContainer
)

gmaps_api_key = os.getenv('GMAPS_API_KEY', None)
if gmaps_api_key is None:
    print('Specify GMAPS_API_KEY as environment variable')
    sys.exit(1)

gmaps = googlemaps.Client(key=gmaps_api_key)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

lang = 'en'


class Places:

    def get_photos(self, photo_ref, id):
        ext = 'jpg'
        file_name = static_tmp_path + '/' + id + '.' + ext
        if os.path.isfile(file_name):
            return request.host_url.replace('http:', 'https:') + os.path.join('static', 'tmp', os.path.basename(file_name))
        with open(file_name, 'wb') as f:
            for chunk in gmaps.places_photo(photo_ref, max_width=640):
                if chunk:
                    f.write(chunk)
        dist_name = os.path.basename(file_name)
        photo_url = request.host_url.replace('http:', 'https:') + os.path.join('static', 'tmp', dist_name)
        return photo_url

    def _format_operating_hours(self, operating_hours):
        today = datetime.now()
        day_index = today.strftime('%w')
        if operating_hours['open_now'] is False:
            return 'Closed Today'
        for period in operating_hours['periods']:
            if 'open' in period:
                if period['open']['day'] == int(day_index):
                    if 'close' not in period:
                        return "24 Hours"
                    else:
                        open_time = datetime.strptime(period['open']['time'], '%H%M').strftime('%H:%M')
                        close_time = datetime.strptime(period['close']['time'], '%H%M').strftime('%H:%M')
                        return "{0} - {1}".format(open_time, close_time)

    def get_place_detail(self, place_id):
        data = dict()
        place_detail_result = gmaps.place(place_id, language=lang)['result']
        data['address'] = place_detail_result['formatted_address']
        data['address_url'] = place_detail_result['url']
        if 'opening_hours' in place_detail_result:
            data['operating_hours'] = self._format_operating_hours(place_detail_result['opening_hours'])
        else:
            data['operating_hours'] = 'N/A'
        if 'rating' in place_detail_result:
            data['rating'] = int(place_detail_result['rating'])
        else:
            data['rating'] = None
        data['name'] = place_detail_result['name']
        data['icon'] = place_detail_result['icon']
        data['types'] = place_detail_result['types']
        if 'website' in place_detail_result:
            data['website'] = place_detail_result['website']
        else:
            data['website'] = None
        return data

    def get_nearby_places(self, lat, lng, type=None):
        location = (lat, lng)
        places = []
        if type is not None:
            nearby_result = gmaps.places_nearby(location=location, radius=100, language=lang, type=type)
        else:
            nearby_result = gmaps.places_nearby(location=location, radius=100, language=lang)
        if nearby_result['status'] != 'OK':
            return "I Couldn't Find Any Places From Your Search. So Sorry.."
        for index in range(len(nearby_result["results"])):
            if len(places) > 6:
                break
            result = nearby_result["results"][index]
            data = self.get_place_detail(result['place_id'])
            if 'photos' in result:
                photo_ref = result['photos'][0]['photo_reference']
                data['photo_url'] = self.get_photos(photo_ref, result['id'])
            else:
                data['photo_url'] = 'https://s.yimg.com/pw/images/en-us/photo_unavailable.png'
            places.append(data)
        return self.create_place_flex_message(places)

    def create_place_flex_message(self, places):
        carousel = CarouselContainer()
        for place in places:
            bubble = {
                "type": "bubble",
                "hero": {
                    "type": "image",
                    "url": place['photo_url'],
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "md",
                            "contents": [
                                {
                                    "type": "icon",
                                    "url": place['icon']
                                },
                                {
                                    "type": "text",
                                    "text": place['name'],
                                    "weight": "bold",
                                    "size": "lg",
                                    "wrap": True
                                }
                            ]
                        }
                    ]
                }
            }
            bubble_body_contents = bubble['body']['contents']
            if place['rating'] is not None:
                bubble_body_contents.append(
                    {
                        "type": "box",
                        "layout": "baseline",
                        "margin": "md",
                        "contents": []
                    }
                )
                bubble_body_rating_contents = bubble['body']['contents'][1]["contents"]
                for star_rating in range(0, place['rating']):
                    bubble_body_rating_contents.append(
                        {
                            "type": "icon",
                            "size": "sm",
                            "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/review_gold_star_28.png"
                        }
                    )
                bubble_body_rating_contents.append(
                    {
                        "type": "text",
                        "text": str(place["rating"]),
                        "size": "sm",
                        "color": "#999999",
                        "margin": "md",
                        "flex": 0
                    }
                )
            bubble_body_contents.append(
                {
                    "type": "box",
                    "layout": "baseline",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": "Place",
                            "color": "#aaaaaa",
                            "size": "sm",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": place["address"],
                            "wrap": True,
                            "color": "#666666",
                            "size": "sm",
                            "flex": 5,
                            "action": {
                                "type": "uri",
                                "uri": place["address_url"]
                            }
                        }
                    ]
                }
            )
            bubble_body_contents.append(
                {
                    "type": "box",
                    "layout": "baseline",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": "Time",
                            "color": "#aaaaaa",
                            "size": "sm",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": place["operating_hours"],
                            "wrap": True,
                            "color": "#666666",
                            "size": "sm",
                            "flex": 5
                        }
                    ]
                }
            )
            if place["website"] is not None:
                bubble["footer"] = {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "Website",
                                "uri": place["website"]
                            }
                        }
                    ]
                }
            bubble_container = BubbleContainer.new_from_json_dict(bubble)
            carousel.contents.append(bubble_container)
        return carousel