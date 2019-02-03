import requests
import time
import os
import datetime
import string
import random
import json
from datetime import timezone
import dateutil.parser
from datetime import timedelta
from linebot.models import (
    BubbleContainer,
    CarouselContainer
)

api_host = os.getenv('FLIGHT_API_HOST', None)
flight_route_api_host = os.getenv('FLIGHT_ROUTE_API', None)
image_host = os.getenv('IMAGE_URL', None)
aircraft_photo_api = os.getenv('AIRCRAFT_PHOTO_API', None)
aircraft_cdn = os.getenv('AIRCRAFT_CDN', None)
hmp_format = '%H:%M %p'
hm_format = '%H:%M'

with open('emoji_flags.json') as cc:
    country_code = json.load(cc)

with open('airports.json') as ap:
    airports = json.load(ap)

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
}

class FlightApi(object):

    def get_aircraft_photo(self, registration_no):
        url = '{0}/api/json/quicksearch.php?term={1}'.format(aircraft_photo_api, registration_no.upper())
        response = requests.get(url, headers=headers)
        print('get_aircraf_photo: {}'.format(response.text))
        resp_json = response.json()
        if len(resp_json) > 0:
            filename = resp_json[0]['filename']
            return '{0}/{1}'.format(aircraft_cdn, filename)
        return None

    def get_latest_flight(self, flight_no):
        # current_milli_time = int(round(time.time() * 1000))
        url = '{0}/api/aircraft/historic/flights/flightNo/{1}'.format(api_host, flight_no)
        response = requests.get(url, headers=headers)
        resp_json = response.json()
        if resp_json['success'] is True and len(resp_json['payload']) > 0:
            return resp_json['payload'][0]
        return None

    def get_country_code_flag(self, name):
        for country in country_code:
            if name.lower() in country['name'].lower():
                return country['emoji']

    def get_airport_name_from_code(self, iata):
        for code, data in airports.items():
            if code == iata:
                country_flag = self.get_country_code_flag(data['country'])
                data['country_flag'] = country_flag
                return data
        return {
            "name": iata,
            "city": iata,
            "country": iata,
            "iata": iata,
            "icao": iata,
            "country_flag": None
        }
    
    def get_flight_metadata(self, flight_no, adshex):
        url = '{0}/api/aircraft/historic/data/0/{1}/{2}'.format(api_host, adshex, flight_no)
        response = requests.get(url, headers=headers)
        return response.json()

    def _convert_epoch_to_hm(self, format, epoch, next_day=False):
        if epoch < 0:
            epoch = abs(epoch)
        convert_time = time.strftime(format, time.gmtime(epoch))
        if next_day is True:
            convert_time += ' (+1)'
        return convert_time
    
    def _convert_epoch_withoffset(self, format, epoch, offset):
        _time = time.gmtime(epoch + offset)
        convert_time = time.strftime(format, _time)
        return convert_time
    
    def _convert_iso_to_epoch(self, iso_dt):
        dt = dateutil.parser.parse(iso_dt)
        return dt.replace(tzinfo=timezone.utc).timestamp()
    
    def _get_timezone_offset(self, iso_dt):
        dt = dateutil.parser.parse(iso_dt)
        return dt.strftime('%z')
    
    def _is_next_day(self, departure_iso, arrival_iso):
        departure = dateutil.parser.parse(departure_iso)
        arrival = dateutil.parser.parse(arrival_iso)
        if arrival.day != departure.day:
            return True
        return False

    def get_flight_schedule(self, flight_no):
        url = '{0}/v2/api/search/structured-search'.format(flight_route_api_host)
        params = {
            'rqid': ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))
        }
        body = {
            'value': flight_no
        }
        response = requests.post(url, params=params, json=body, headers=headers)
        flights = response.json()
        for flight in flights:
            flight_name = '{0}{1}'.format(flight['_source']['carrierIata'], flight['_source']['flightNumber'])
            if flight_name == flight_no:
                result = {}
                result['departureTime'] = self._convert_iso_to_epoch(flight['_source']['departureDateTime'])
                result['departureTZOffset'] = self._get_timezone_offset(flight['_source']['departureDateTime'])
                result['arrivalTime'] = self._convert_iso_to_epoch(flight['_source']['arrivalDateTime'])
                result['arrivalTZOffset'] = self._get_timezone_offset(flight['_source']['arrivalDateTime'])
                result['isNextDay'] = self._is_next_day(flight['_source']['departureDateTime'], flight['_source']['arrivalDateTime'])
                return result
        return None
    

    def create_flight_message(self, flight_no, adshex, payload):
        departure_airport = payload['static']['departureApt']
        arrival_airport = payload['static']['arrivalApt']
        print(json.dumps(payload))
        bubble = {
            "type": "bubble",
            "direction": "ltr",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "{0} - {1}".format(flight_no, payload['aircraft']['aircraftOperator']).upper(),
                        "size": "sm",
                        "wrap": True,
                        "align": "center",
                        "weight": "bold",
                        "color": "#383838"
                    }
                ]
            },
            "body": {    
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
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
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {
                                    "type": "text",
                                    "text": self.get_airport_name_from_code(payload['static']['departureApt'])['city'],
                                    "align": "start",
                                    "gravity": "top",
                                    "wrap": True
                                },
                                {
                                "type": "text",
                                "text": departure_airport,
                                "size": "xxl",
                                "action": {
                                    "type": "postback",
                                    "data": "airport={0}".format(departure_airport)
                                }
                                }
                            ]
                            },
                            {
                                "type": "image",
                                "url": "https://i.ibb.co/mvg5f11/travel-icon-38032.png",
                                "size": "xs",
                                "backgroundColor": "#FFFFFF"
                            },
                            {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": self.get_airport_name_from_code(payload['static']['arrivalApt'])['city'],
                                    "align": "end",
                                    "gravity": "top",
                                    "wrap": True
                                },
                                {
                                "type": "text",
                                "text": arrival_airport,
                                "size": "xxl",
                                "align": "end",
                                "weight": "regular",
                                "wrap": True,
                                "action": {
                                    "type": "postback",
                                    "data": "airport={0}".format(arrival_airport)
                                }
                                }
                            ]
                            }
                        ]
                        },
                        {
                        "type": "separator"
                        }
                    ]
                    }
                ]
            }
        }

        if len(payload['photos']) > 0:
            aircraft_photo_url = payload['photos'][0]['url']
        else:
            aircraft_photo_url = self.get_aircraft_photo(payload['aircraft']['registration'])
        
        if aircraft_photo_url is not None:
            bubble['hero'] = {
                "type": "image",
                "url": aircraft_photo_url,
                "size": "full",
                "aspectRatio": "1.51:1",
                "aspectMode": "cover"
            }
        
        if payload['status']['depSchdLOC'] is None:
            flight_schedule = self.get_flight_schedule(flight_no)
            if flight_schedule is not None:
                payload['status']['depSchdLOC'] = flight_schedule['departureTime']
                payload['status']['depOffset'] = flight_schedule['departureTZOffset']
                payload['status']['arrSchdLOC'] = flight_schedule['arrivalTime']
                payload['status']['arrOffset'] = flight_schedule['arrivalTZOffset']
                next_day = flight_schedule['isNextDay']

        if payload['status']['depSchdLOC'] is not None:
            next_day = False
            if payload['static']['arrivalDay'] == 'Next day':
                next_day = True
            bubble['body']['contents'][0]['contents'].extend(
                (
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                            "type": "text",
                            "text": "Departure",
                            "flex": 1,
                            "size": "xs"
                            },
                            {
                            "type": "text",
                            "text": "Arrival",
                            "size": "xs",
                            "align": "end"
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                            "type": "text",
                            "text": self._convert_epoch_to_hm(hmp_format, payload['status']['depSchdLOC'], False),
                            "size": "xs",
                            "weight": "bold"
                            },
                            {
                            "type": "text",
                            "text": self._convert_epoch_to_hm(hmp_format, payload['status']['arrSchdLOC'], next_day),
                            "size": "xs",
                            "align": "end",
                            "weight": "bold"
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                            "type": "text",
                            "text": 'UTC{0}'.format(payload['status']['depOffset']),
                            "size": "xs"
                            },
                            {
                            "type": "text",
                            "text": "UTC{0}".format(payload['status']['arrOffset']),
                            "size": "xs",
                            "align": "end"
                            }
                        ]
                        }
                    ]
            },
            {
                "type": "separator"
            }
            )
            )
        bubble['body']['contents'][0]['contents'].extend(
            (
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
                        "text": "Aircraft Type",
                        "size": "xs"
                        },
                        {
                        "type": "text",
                        "text": "{0} ({1})".format(payload['aircraft']['aircraftFullType'], payload['aircraft']['aircraftAgeString']),
                        "size": "xs",
                        "color": "#545454"
                        },
                        {
                            "type": "text",
                            "text": "Seats: {0}".format(payload['static']['seats']),
                            "size": "xs",
                            "color": "#545454"
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
                "contents": [
                    {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "text",
                        "text": "Terminal",
                        "size": "xs"
                        },
                        {
                        "type": "text",
                        "text": payload['status']['departureTerminal'] if payload['status']['departureTerminal'] is not None else "N/A",
                        "size": "xs",
                        "color": "#545454"
                        }
                    ]
                    },
                    {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "text",
                        "text": "Gate",
                        "size": "xs"
                        },
                        {
                        "type": "text",
                        "text": payload['status']['departureGate'] if payload['status']['departureGate'] is not None else "N/A",
                        "size": "xs",
                        "color": "#545454"
                        }
                    ]
                    },
                    {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "text",
                        "text": "Travel Time",
                        "size": "xs"
                        },
                        {
                        "type": "text",
                        "text": payload['static']['journeyTime'],
                        "size": "xs",
                        "color": "#545454"
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
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "text",
                        "text": "Code Share",
                        "size": "xs"
                        },
                        {
                        "type": "text",
                        "text": " / ".join(payload['static']['codeshares']) if payload['static']['codeshares'] is not None else 'N/A',
                        "size": "xs",
                        "color": "#545454",
                        "wrap": True
                        }
                    ]
                }
            )
        )
        return BubbleContainer.new_from_json_dict(bubble)

    def get_aircraft_by_flight_no(self, flight_no):
        result = self.get_latest_flight(flight_no)
        if result is not None:
            return result['type']
        return 'N/A'
    
    def get_airport_code(self, query):
        url = '{0}/data/endpoints/search_ajax.php'.format(api_host)
        params = {
            'searchText': query,
            'key': 'PF2202'
        }
        response = requests.get(url, headers=headers, params=params)
        resp_json = response.json()
        return resp_json['airports'] if len(resp_json['airports']) > 0 else None

    def get_flight_by_route(self, origin, destination):
        print('ORIGIN: {0}, DESTINATION: {1}'.format(origin, destination))
        today = datetime.datetime.today()
        url = '{0}/v2/api-next/flight-tracker/route/{1}/{2}/{3}/{4}/{5}'.format(flight_route_api_host, origin, destination, today.year, today.month, today.day)
        params = {
            'numHours': '24',
            'rqid': ''.join(random.choices(string.ascii_lowercase + string.digits, k=11)),
            'hour': '0'
        }
        response = requests.get(url, params=params)
        resp_json = response.json()['data']
        result = {}
        if len(resp_json['flights']) > 0:
            flights = []
            for flight in resp_json['flights']:
                if 'isCodeshare' not in flight:
                    flight_no = '{0}{1}'.format(flight['carrier']['fs'], flight['carrier']['flightNumber']).replace('*','')
                    flights.append({
                        'time': '{0} → {1}'.format(flight['departureTime']['timeAMPM'], flight['arrivalTime']['timeAMPM']),
                        'flight_no': flight_no,
                        'carrier_name': flight['carrier']['name']
                    })
                result['title'] = 'Up To {0} Flights Per Day'.format(len(flights))
                result['description'] = '{0} ({1}) to {2} ({3})'.format(resp_json['header']['departureAirport']['city'],
                                                                        resp_json['header']['departureAirport']['iata'],
                                                                        resp_json['header']['arrivalAirport']['city'],
                                                                        resp_json['header']['arrivalAirport']['iata'])
            result['flights'] = flights
            return result
        return None
    
    def create_flight_route_message(self, data, paging=10):
        carousel_container = CarouselContainer()
        pages = [data['flights'][i: i+paging] for i in range(0, len(data['flights']), paging)]
        for page in pages:
            bubble = {
                "type": "bubble",
                "direction": "ltr",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": data['title'],
                                    "size": "sm",
                                    "align": "start",
                                    "weight": "bold",
                                    "color": "#000000"
                                },
                                {
                                    "type": "text",
                                    "text": data['description'],
                                    "size": "xs",
                                    "color": "#929292",
                                    "wrap": True
                                }
                            ]
                        },
                        {
                            "type": "separator"
                        }
                    ]
                }
            }
            for flight in page:
                bubble_contents = bubble['body']['contents'].extend(
                    (
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "flex": 2,
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": flight['time'],
                                            "size": "xs",
                                            "gravity": "top",
                                            "color": "#000000",
                                            "action": {
                                                "type": "postback",
                                                "label": "flight_info={0}".format(flight['flight_no']),
                                                "data": "flight_info={0}".format(flight['flight_no'])
                                            }
                                        },
                                        {
                                            "type": "text",
                                            "text": flight['carrier_name'],
                                            "size": "xs",
                                            "color": "#878787",
                                            "wrap": True,
                                            "action": {
                                                "type": "postback",
                                                "label": "flight_info={0}".format(flight['flight_no']),
                                                "data": "flight_info={0}".format(flight['flight_no'])
                                            }
                                        }
                                    ]
                                },
                                {
                                    "type": "text",
                                    "text": flight['flight_no'],
                                    "size": "lg",
                                    "align": "center",
                                    "color": "#269CB0",
                                    "align": "center",
                                    "gravity": "center",
                                    "action": {
                                        "type": "postback",
                                        "label": "flight_info={0}".format(flight['flight_no']),
                                        "data": "flight_info={0}".format(flight['flight_no'])
                                    }
                                }
                            ]
                        },
                        {
                            "type": "separator"
                        }
                    )
                )
            bubble_container = BubbleContainer.new_from_json_dict(bubble)
            carousel_container.contents.append(bubble)
            if len(carousel_container.contents) == 7:
                break 
        return carousel_container
    
    def get_airport_data(self, airport_iata, limit=15):
        url = '{0}/api/airport/times/{1}'.format(api_host, airport_iata)
        response = requests.get(url, headers=headers)
        resp_json = response.json()['payload']
        if resp_json['departures'] is not None and resp_json['arrivals'] is not None:
            result = {}
            airport = self.get_airport_name_from_code(airport_iata)
            airport_country = '{0} {1}'.format(airport['country'], airport['country_flag'], ) if airport['country_flag'] is not None else airport['country']
            result['departure_title'] = '{0}, {1}, {2} ({3})'.format(airport['name'], airport['city'], airport_country, airport_iata)
            result['arrival_title'] = '{0}, {1}, {2} ({3})'.format(airport['name'], airport['city'], airport_country, airport_iata)
            result['departures'] = []
            result['arrivals'] = []
            departure_length = limit if len(resp_json['departures']) > limit else len(resp_json['departures'])
            for index in range(0, departure_length-1):
                departure = resp_json['departures'][index]
                departure_time = departure['estimatedTime'] if departure['estimatedTime'] is not None else departure['scheduledTime']
                destination_airport = self.get_airport_name_from_code(departure['airport'])
                departure_city = '{0} {1}'.format(destination_airport['country_flag'], destination_airport['city'].upper()) if destination_airport['country_flag'] is not None else destination_airport['city'].upper()
                result['departures'].append(
                    {
                        'time': self._convert_epoch_withoffset('%H:%M', departure_time, departure['offset']),
                        'destination': departure_city,
                        'destination_code': destination_airport['iata'],
                        'flight_no': departure['flightNumber']
                    }
                )
            arrival_length = limit if len(resp_json['arrivals']) > limit else len(resp_json['arrivals'])
            for index in range(0, arrival_length-1):
                arrival = resp_json['arrivals'][index]
                arrival_time = arrival['scheduledTime']
                origin_airport = self.get_airport_name_from_code(arrival['airport'])
                origin_city = '{0} {1}'.format(origin_airport['country_flag'], origin_airport['city'].upper()) if origin_airport['country_flag'] is not None else origin_airport['city'].upper()
                result['arrivals'].append(
                    {
                        'time': self._convert_epoch_withoffset('%H:%M', arrival_time, arrival['offset']),
                        'origin': origin_city,
                        'origin_code': origin_airport['iata'],
                        'flight_no': arrival['flightNumber']
                    }
                )    
            return result
        return None
        
    def create_airport_message(self, airport_data):
        carousel_container = CarouselContainer()
        departures_bubble = {
            "type": "bubble",
            "styles": {
                "header": {
                    "backgroundColor": "#FFF800"
                },
                "body": {
                    "backgroundColor": "#000000"
                }
            },
            "direction": "ltr",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": 'DEPARTURES',
                        "align": "start",
                        "size": "xl",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": airport_data['departure_title'],
                        "size": "xs",
                        "align": "start",
                        "wrap": True
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "Time",
                                "flex": 1,
                                "size": "xs",
                                "align": "start",
                                "color": "#FFFFFF"
                            },
                            {
                                "type": "text",
                                "text": "Destination",
                                "flex": 2,
                                "size": "xs",
                                "align": "start",
                                "color": "#FFFFFF"
                            },
                            {
                                "type": "text",
                                "text": "Flight",
                                "size": "xs",
                                "align": "end",
                                "color": "#FFFFFF"
                            }
                        ]
                    },
                    {
                        "type": "separator"
                    }
                ]
            }
        }
        for departure in airport_data['departures']:
            departures_bubble['body']['contents'].append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": departure['time'],
                            "flex": 1,
                            "size": "xs",
                            "align": "start",
                            "color": "#FFFFFF"
                        },
                        {
                            "type": "text",
                            "text": departure['destination'],
                            "flex": 2,
                            "size": "xs",
                            "align": "start",
                            "color": "#FFFFFF",
                            "wrap": True,
                            "action": {
                                "type": "postback",
                                "data": "airport={0}".format(departure['destination_code'])
                            }
                        },
                        {
                            "type": "text",
                            "text": departure['flight_no'],
                            "size": "xs",
                            "align": "end",
                            "color": "#FFFFFF",
                            "action": {
                                "type": "postback",
                                "data": "flight_info={0}".format(departure['flight_no'])
                            }
                        }
                    ]
                }
            )
        arrivals_bubble = {
            "type": "bubble",
            "styles": {
                "header": {
                    "backgroundColor": "#9FE9FF"
                },
                "body": {
                    "backgroundColor": "#000000"
                }
            },
            "direction": "ltr",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "ARRIVALS",
                        "align": "start",
                        "size": "xl",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": airport_data['arrival_title'],
                        "align": "start",
                        "size": "xs",
                        "wrap": True
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "Time",
                                "flex": 1,
                                "size": "xs",
                                "align": "start",
                                "color": "#FFFFFF"
                            },
                            {
                                "type": "text",
                                "text": "Origin",
                                "flex": 2,
                                "size": "xs",
                                "align": "start",
                                "color": "#FFFFFF"
                            },
                            {
                                "type": "text",
                                "text": "Flight",
                                "size": "xs",
                                "align": "end",
                                "color": "#FFFFFF"
                            }
                        ]
                    },
                    {
                        "type": "separator"
                    }
                ]
            }
        }
        for arrival in airport_data['arrivals']:
            arrivals_bubble['body']['contents'].append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": arrival['time'],
                            "flex": 1,
                            "size": "xs",
                            "align": "start",
                            "color": "#FFFFFF"
                        },
                        {
                            "type": "text",
                            "text": arrival['origin'],
                            "flex": 2,
                            "size": "xs",
                            "align": "start",
                            "color": "#FFFFFF",
                            "wrap": True,
                            "action": {
                                "type": "postback",
                                "data": "airport={0}".format(arrival['origin_code'])
                            }
                        },
                        {
                            "type": "text",
                            "text": arrival['flight_no'],
                            "size": "xs",
                            "align": "end",
                            "color": "#FFFFFF",
                            "action": {
                                "type": "postback",
                                "data": "flight_info={0}".format(arrival['flight_no'])
                            }
                        }
                    ]
                }
            )
        departure_container = BubbleContainer.new_from_json_dict(departures_bubble)
        arrival_container = BubbleContainer.new_from_json_dict(arrivals_bubble)
        carousel_container.contents.append(departure_container)
        carousel_container.contents.append(arrival_container)
        return carousel_container

if __name__ == "__main__":
    flight_api = FlightApi()
    print(flight_api._convert_epoch_withoffset('%H:%M', 1544272200, -21600))