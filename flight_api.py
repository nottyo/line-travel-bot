import requests
import time
import os
import datetime
import string
import random
import json
from datetime import timedelta
from linebot.models import (
    BubbleContainer,
    CarouselContainer
)

api_host = os.getenv('FLIGHT_API_HOST', None)
flight_route_api_host = os.getenv('FLIGHT_ROUTE_API', None)
hmp_format = '%H:%M %p'
hm_format = '%H:%M'

class FlightApi(object):

    def get_latest_flight(self, flight_no):
        current_milli_time = int(round(time.time() * 1000))
        url = '{0}/endpoints/playback/previousFlights.php?fn={1}&_={2}'.format(api_host, flight_no, current_milli_time)
        response = requests.get(url)
        resp_json = response.json()
        if resp_json['flights'] is not False and len(resp_json['flights']) > 0:
            return resp_json['flights'][0]
        return None
    
    def get_flight_metadata(self, flight_no, adshex):
        url = '{0}/api/api.php'.format(api_host)
        params = {
            'r': 'aircraftMetadata',
            'adshex': adshex,
            'flightno': flight_no,
            'type': '0',
            'isPlayback': '0',
            'isPoll': '0'
        }
        response = requests.get(url, params=params)
        return response.json()

    def _convert_epoch_to_hm(self, format, epoch, next_day=False):
        if epoch < 0:
            epoch = abs(epoch)
        convert_time = time.strftime(format, time.gmtime(epoch))
        if next_day is True:
            convert_time += ' (+1)'
        return convert_time

    def create_flight_message(self, flight_no, adshex, flight_metadata):
        departure_airport = flight_metadata['flightData']['departureApt']
        arrival_airport = flight_metadata['flightData']['arrivalApt']
        bubble = {
            "type": "bubble",
            "direction": "ltr",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "{0} - {1}".format(flight_no, flight_metadata['aircraftData']['aicraftOperator']).upper(),
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
                                    "text": flight_metadata['airportDetail'][departure_airport]['airportCity'],
                                    "align": "start",
                                    "gravity": "top",
                                    "wrap": True
                                },
                                {
                                "type": "text",
                                "text": departure_airport,
                                "size": "xxl"
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
                                    "text": flight_metadata['airportDetail'][arrival_airport]['airportCity'],
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

        if flight_metadata['photos'] is not None:
            bubble['hero'] = {
                "type": "image",
                "url": flight_metadata['photos'][0]['thumbnailPath'],
                "size": "full",
                "aspectRatio": "1.51:1",
                "aspectMode": "cover"
            }
        else:
            bubble['hero'] = {
                "type": "image",
                "url": "https://flightstat.planefinder.net/v1/getImage.php?airlineCode={0}&aircraftType={1}".format(flight_metadata['aircraftData']['airlineICAO'], flight_metadata['aircraftData']['typeCode']),
                "size": "full",
                "aspectRatio": "1.91:1",
                "aspectMode": "fit",
                "backgroundColor": "#5290CC"
            }
        
        if flight_metadata['statusData']['depSchdLOC'] is not None:
            next_day = False
            if flight_metadata['flightData']['arrivalDay'] == 'Next day':
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
                            "text": self._convert_epoch_to_hm(hmp_format, flight_metadata['statusData']['depSchdLOC'], False),
                            "size": "xs",
                            "weight": "bold"
                            },
                            {
                            "type": "text",
                            "text": self._convert_epoch_to_hm(hmp_format, flight_metadata['statusData']['arrSchdLOC'], next_day),
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
                            "text": "UTC+{0}".format(self._convert_epoch_to_hm(hm_format, flight_metadata['statusData']['depOffset'])) if flight_metadata['statusData']['depOffset'] > 0 else "UTC-{0}".format(self._convert_epoch_to_hm(hm_format, flight_metadata['statusData']['depOffset'])),
                            "size": "xs"
                            },
                            {
                            "type": "text",
                            "text": "UTC+{0}".format(self._convert_epoch_to_hm(hm_format, flight_metadata['statusData']['arrOffset'])) if flight_metadata['statusData']['arrOffset'] > 0 else "UTC-{0}".format(self._convert_epoch_to_hm(hm_format, flight_metadata['statusData']['arrOffset'])),
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
                        "text": "{0} ({1})".format(flight_metadata['aircraftData']['aircraftFullType'], flight_metadata['aircraftData']['aircraftAgeString']),
                        "size": "xs",
                        "color": "#545454"
                        },
                        {
                            "type": "text",
                            "text": "Seats: {0}".format(flight_metadata['flightData']['seats']),
                            "size": "xs",
                            "color": "#545454"
                        }
                    ]
                    },
                    {
                    "type": "image",
                    "url": "https://flightstat.planefinder.net/v2/getLogo3x.php?airlineCode={0}&requestThumb=0&hex={1}".format(flight_metadata['aircraftData']['airlineICAO'], adshex),
                    "size": "xs"
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
                        "text": flight_metadata['flightData']['departureTerminal'] if flight_metadata['flightData']['departureTerminal'] is not None else "N/A",
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
                        "text": flight_metadata['flightData']['departureGate'] if flight_metadata['flightData']['departureGate'] is not None else "N/A",
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
                        "text": flight_metadata['flightData']['journeyTime'],
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
                        "text": " / ".join(flight_metadata['flightData']['codeshares']) if flight_metadata['flightData']['codeshares'] is not None else 'N/A',
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