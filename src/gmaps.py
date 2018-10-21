import boto3
import copy
from datetime import datetime, timedelta
from decimal import Decimal
import googlemaps
import hashlib
import http.cookies
import json
from math import radians, degrees, cos, sin, asin, sqrt, fabs, log, tan, pi, atan2
import os
import traceback
import urllib
import uuid
from sneks.sam import events
from sneks.sam.response_core import make_response, redirect
from sneks.sam.ui_stuff import loader_for, make_404

GMAPS_API_KEY = "AIzaSyDELQPc2vQNkk81bcM3f-4nOmcKuRbIV6k"

TEAM_COOKIE_KEY = "astronav-team"

TEAM_TABLE = boto3.resource("dynamodb").Table(os.environ["TEAM_TABLE"])
ROUTE_TABLE = boto3.resource("dynamodb").Table(os.environ["ROUTE_TABLE"])
IMAGE_TABLE = boto3.resource("dynamodb").Table(os.environ["IMAGE_TABLE"])

def bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    startLat, startLong, endLat, endLong = map(radians, [lat1, lon1, lat2, lon2])
    dPhi = log(tan(endLat/2.0+pi/4.0)/tan(startLat/2.0+pi/4.0))
    if abs(dLong) > pi:
        if dLong > 0.0:
            dLong = -(2.0 * pi - dLong)
        else:
            dLong = (2.0 * pi + dLong)
    bearing = (degrees(atan2(dLong, dPhi)) + 360.0) % 360.0
    return bearing

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    # https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000 # Radius of earth in meters. Use 3959 for miles or 20903520 for feet
    return c * r

def minimize_gps(point, distance=1):
    latitude = point["lat"]
    longitude = point["lng"]
    lat_str = str(latitude)
    lng_str = str(longitude)
    _lat_str = lat_str
    _lng_str = lng_str
    while haversine(latitude, longitude, float(_lat_str), float(_lng_str)) < distance:
        lat_str = _lat_str
        lng_str = _lng_str
        if len(_lat_str.split(".")[1]) >= len(_lng_str.split(".")[1]):
            _lat_str = _lat_str[:-1]
        if len(_lat_str.split(".")[1]) <= len(_lng_str.split(".")[1]):
            _lng_str = _lng_str[:-1]
    return {"lat":Decimal(lat_str), "lng":Decimal(lng_str)}

def load_route_from_google(addresses):
    kwargs = {
        "origin":addresses[0],
        "destination":addresses[-1],
        "mode":"walking",
        "waypoints":addresses[1:-1],
        "optimize_waypoints":True,
        "avoid":["tolls","ferries"]
    }
    gmaps = googlemaps.Client(key=GMAPS_API_KEY)
    route = gmaps.directions(**kwargs)[0]
    return route

def load_coordinates_from_google(address):
    print("Loading address from google maps: {}".format(address))
    gmaps = googlemaps.Client(key=GMAPS_API_KEY)
    geocode_results = gmaps.geocode(address)
    geocode_result = geocode_results[0]
    return minimize_gps(geocode_result["geometry"]["location"])

def convert_python_route_to_javascript(route):
    response = {"routes":[copy.deepcopy(route)]}
    route = response["routes"][0]
    start_address = route["legs"][0]["start_address"]
    waypoints = [l["start_address"] for l in route["legs"][1:]]
    end_address = route["legs"][-1]["end_address"]
    response["request"] = {
        "destination":{"query":end_address},
        "origin":{"query":start_address},
        "optimizeWaypoints":True,
        "travelMode": "WALKING",
        "unitSystem": 1,
        "waypoints":[{"location":{"query":addr},"stopover":True} for addr in waypoints]
    }
    for route in response["routes"]:
        route["bounds"] = {
            "east": route["bounds"]["northeast"]["lng"],
            "north": route["bounds"]["northeast"]["lat"],
            "south": route["bounds"]["southwest"]["lat"],
            "west": route["bounds"]["southwest"]["lng"]
        }
        for leg in route["legs"]:
            leg["start_location"] = minimize_gps(leg["start_location"])
            leg["end_location"] = minimize_gps(leg["end_location"])
            for step in leg["steps"]:
                step["start_location"] = minimize_gps(step["start_location"])
                step["end_location"] = minimize_gps(step["end_location"])
                step["instructions"] = step["html_instructions"]
                step["path"] = [step["start_location"], step["end_location"]]
        route["overview_path"] = [route["legs"][0]["start_location"], route["legs"][-1]["end_location"]]
    return response
