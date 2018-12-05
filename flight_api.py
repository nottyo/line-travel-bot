import requests
import time
import os
from linebot.models import (
    BubbleContainer
)

api_host = os.getenv('FLIGHT_API_HOST', None)
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
                        "color": "#545454"
                        }
                    ]
                }
            )
        )
        return BubbleContainer.new_from_json_dict(bubble)

if __name__ == "__main__":
    flight_api = FlightApi()
    print(flight_api._convert_epoch_to_hm(hmp_format, 1544007000))
    print(flight_api._convert_epoch_to_hm(hm_format, 21600))