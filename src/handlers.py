import boto3A
import copy
import googlemaps
import hashlib
import json
from math import radians, degrees, cos, sin, asin, sqrt, fabs, log, tan, pi, atan2
import os
import traceback
import urllib
from sneks.sam.ui_stuff import loader_for

GMAPS_API_KEY = "AIzaSyDELQPc2vQNkk81bcM3f-4nOmcKuRbIV6k"

ADDRESS_TABLE = boto3.resource("dynamodb").Table(os.environ["ADDRESS_TABLE"])
TEAM_TABLE = boto3.resource("dynamodb").Table(os.environ["TEAM_TABLE"])
ROUTE_TABLE = boto3.resource("dynamodb").Table(os.environ["ROUTE_TABLE"])

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
    return {"lat":float(lat_str), "lng":float(lng_str)}

def load_address_from_db(address):
    try:
        return ADDRESS_TABLE.get_item(Key={"address":address})["Item"]
    except:
        return None

def load_points_for_address(address):
    item = load_address_from_db(address)
    if not item:
        print("Loading address from google maps: {}".format(address))
        gmaps = googlemaps.Client(key=GMAPS_API_KEY)
        geocode_results = gmaps.geocode(address)
        geocode_result = geocode_results[0]
        lat = geocode_result["geometry"]["location"]["lat"]
        lon = geocode_result["geometry"]["location"]["lng"]
        item = {
            "address":address,
            "latitude":str(lat),
            "longitude":str(lon),
            "geocode_results":json.dumps(geocode_results)
        }
        ADDRESS_TABLE.put_item(Item=item)
    else:
        print("Loaded address from database: {}".format(address))
    return (item["latitude"], item["longitude"])

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
    directions = gmaps.directions(**kwargs)[0]

def get_distance(addresses):
    distance = 0
    for i in len(addresses):
        start = addresses[i]
        end = addresses[i+1%len(addresses)]
        distance += haversine(start["lat"], start["lon"], end["lat"], end["lon"])
    return distance

def approximate_tsp(addresses):
    route = copy.deepcopy(addresses)
    order = "/".join([a["address"] for a in route])
    current_distance = get_distance(addresses)
    previous_order = None
    while not order == previous_order:
        previous_order = order
        for i in range(len(addresses)):
            for j in range(len(addresses)):
                if i != j:
                    new_route = copy.deepcopy(route)
                    new_route[i] = route[j]
                    new_route[j] = route[i]
                    new_distance = get_distance(new_route)
                    if new_distance < current_distance:
                        current_distance = new_distance
                        route = new_route
        order = "/".join([a["address"] for a in route])
    return route

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

@loader_for("route.html")
# @loader_for("message.html.jinja")
def submit_waypoints(event, *args, **kwargs):
    body = urllib.parse.parse_qs(event["body"])
    addresses = body.get("address_area",[])
    if addresses:
        addresses = [x.strip() for x in addresses[0].split("\n") if x.strip()]
    address_map = {}
    max_lat = -200.0
    max_lon = -200.0
    min_lat = 200.0
    min_lon = 200.0
    for address in addresses:
        lat, lon = load_points_for_address(address)
        lat = float(lat)
        lon = float(lon)
        max_lat = max(lat, max_lat)
        max_lon = max(lon, max_lon)
        min_lat = min(lat, min_lat)
        min_lon = min(lon, min_lon)
        address_map[address] = {"lat":lat, "lon":lon}
    center_lat = (max_lat - min_lat)/2 + min_lat
    center_lon = (max_lon - min_lon)/2 + min_lon
    address_list = [{"address":k,"lat":address_map[k]["lat"],"lon":address_map[k]["lon"]} for k in address_map]
    route = approximate_tsp(address_list)
    info = {
        "lat_range":(min_lat, center_lat, max_lat),
        "lon_range":(min_lon, center_lon, max_lon),
        "addresses":address_map,
        "address_list":route
    }
    params = {
        "message_title":"Waypoints:",
        "GMAPS_KEY":GMAPS_API_KEY,
        "ROUTE_INFO":json.dumps(info, indent=2, sort_keys=True)
    }
    return params

@loader_for("route.html")
def get_route(event, *args, **kwargs):
    body = urllib.parse.parse_qs(event["body"])
    addresses = body.get("address_area",[])
    if addresses:
        addresses = [x.strip() for x in addresses[0].split("\n") if x.strip()]

    address_map = {}
    max_lat = -200.0
    max_lon = -200.0
    min_lat = 200.0
    min_lon = 200.0
    for address in addresses:
        lat, lon = load_points_for_address(address)
        lat = float(lat)
        lon = float(lon)
        max_lat = max(lat, max_lat)
        max_lon = max(lon, max_lon)
        min_lat = min(lat, min_lat)
        min_lon = min(lon, min_lon)
        address_map[address] = {"lat":lat, "lon":lon}
    center_lat = (max_lat - min_lat)/2 + min_lat
    center_lon = (max_lon - min_lon)/2 + min_lon
    address_list = [{"address":k,"lat":address_map[k]["lat"],"lon":address_map[k]["lon"]} for k in address_map]
    route = approximate_tsp(address_list)
    info = {
        "lat_range":(min_lat, center_lat, max_lat),
        "lon_range":(min_lon, center_lon, max_lon),
        "addresses":address_map,
        "address_list":route
    }
    params = {
        "message_title":"Waypoints:",
        "GMAPS_KEY":GMAPS_API_KEY,
        "ROUTE_INFO":json.dumps(info, indent=2, sort_keys=True)
    }
    return params

def load_route_from_db(route_id):
    try:
        return ROUTE_TABLE.get_item(Key={"route_id":route_id})["Item"]
    except:
        traceback.print_exc()
        return None

def get_route_id(addresses):
    route_id = hashlib.md5("\n".join([a.upper() for a in addresses]).encode("utf-8")).hexdigest()
    return route_id

def load_route(addresses):
    route_id = get_route_id(addresses)
    item = load_route_from_db(route_id)
    if item:
        print("Route {} loaded from database.".format(route_id))
    else:
        print("Loading route {} from google maps.".format(route_id))
        route = load_route_from_google(addresses)
        item = {
            "route_id":route_id,
            "result":json.dumps(route, separators=(',',':'))
        }
        ROUTE_TABLE.put_item(Item=item)
        print("Route {} loaded from google maps and cached.".format(route_id))
    return 


def cache_google_result(event, *args, **kwargs):
    result = json.loads(event["body"])
