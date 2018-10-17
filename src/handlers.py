import boto3
import copy
import googlemaps
import hashlib
import json
from math import radians, degrees, cos, sin, asin, sqrt, fabs, log, tan, pi, atan2
import os
import traceback
import urllib
import uuid
from sneks.sam import events
from sneks.sam.response_core import make_response
from sneks.sam.ui_stuff import loader_for, make_404

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

def convert_python_route_to_javascript(route):
    if isinstance(route, str):
        route = deepload(route)
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

def deepload(s):
    while True:
        try:
            s = json.loads(s)
        except:
            break
    if isinstance(s, list):
        s = [deepload(x) for x in s]
    if isinstance(s, dict):
        s = {k:deepload(s[k]) for k in s}
    return s

def store_route(event, *args, **kwargs):
    body = deepload(event["body"])
    if "addresses" in body:
        route_id, response, item = load_route(addresses=body["addresses"])
    elif "route_id" in body:
        route_id, response, item = load_route(route_id=body["route_id"])
    else:
        return make_404(event)
    if not response:
        return make_404(event)
    # return {"route_id":route_id,"route_result":result}
    return make_response({"redirect":events.base_path(event) + "/route_map.html?route_id={}".format(route_id)})

@loader_for("route_map.html")
def view_route(event, *args, **kwargs):
    params = event.get("multiValueQueryStringParameters",{})
    route_ids = params.get("route_id",[])
    if not route_ids:
        return make_404(event)
    route_id = route_ids[0]
    route_id, response, item = load_route(route_id=route_id)
    if not response:
        return make_404(event)
    return {
        "route_id":route_id,
        "js_data":json.dumps(response, sort_keys=True, separators=(',',':')),
        "distance":format_distance(item["distance"]),
        "duration":format_time(item["duration"]),
        "addresses":item["addresses"]
    }

def format_distance(meters):
    meters = int(meters)
    miles = meters/1609.34
    if miles >= 100:
        return "{:.0f} miles".format(miles)
    if miles > .5:
        return "{:.1f} miles".format(miles)
    feet = miles * 5280
    return "{:.0f} feet".format(feet)

def format_time(seconds):
    seconds = int(seconds)
    minutes = int(seconds/60)
    seconds = seconds - 60*minutes
    if seconds > 30:
        minutes += 1
    hours = int(minutes/60)
    minutes = minutes - hours*60
    days = int(hours/24)
    hours = hours - days*24
    if days > 0:
        return "{}:{:0>2d}:{:0>2d}".format(days, hours, minutes)
    else:
        return "{:0>2d}:{:0>2d}".format(hours, minutes)

@loader_for("route_list.html")
def list_routes_handler(event, *args, **kwargs):
    params = event.get("multiValueQueryStringParameters",{})
    params = params if params else {}
    last_routes = params.get("last_route",[])
    if not last_routes:
        last_route = None
    else:
        last_route = last_routes[0]
    routes, new_last_route = list_routes(last_route=last_route)
    routes = [r for r in routes if r.get("addresses")]
    for route in routes:
        route["addresses"] = deepload(route["addresses"])
        route["num_locations"] = len(route["addresses"])
        route["distance"] = format_distance(route.get("distance")) if route.get("distance") else "???"
        route["duration"] = format_time(route.get("duration")) if route.get("duration") else "???"
    return {"routes":routes,"last_route":new_last_route}

def list_routes(last_route=None):
    kwargs = {
        "Select":"SPECIFIC_ATTRIBUTES",
        # "ProjectionExpression":"route_id, addresses, duration, distance",
        "ProjectionExpression":"#RID, #ADR, #DUR, #DIS",
        "ExpressionAttributeNames":{
            "#RID":"route_id",
            "#ADR":"addresses",
            "#DUR":"duration",
            "#DIS":"distance"
        }
    }
    if last_route:
        kwargs["ExclusiveStartKey"] = {"route_id":last_route}
    response = ROUTE_TABLE.scan(**kwargs)
    new_last_route = None
    if response.get("LastEvaluatedKey",None):
        new_last_route = response["LastEvaluatedKey"]["route_id"]
    return response["Items"], new_last_route

def load_route_from_db(route_id):
    try:
        item = ROUTE_TABLE.get_item(Key={"route_id":route_id})["Item"]
        if item.get("route") and convert_python_route_to_javascript(item["route"]):
            # Make sure it contains a result and that the result can be parsed.
            return item
    except:
        traceback.print_exc()
    return None

def get_route_id(addresses):
    route_id = hashlib.md5("\n".join([a.strip().upper() for a in addresses]).encode("utf-8")).hexdigest()
    return route_id

def ensure_all_fields_filled(item):
    changed = False
    route = deepload(item["route"])
    if "addresses" not in item:
        addresses = [l["start_address"] for l in route["legs"]]
        addresses.append(route["legs"][-1]["end_address"])
        item["addresses"] = addresses
        changed = True
    if "distance" not in item:
        distance = 0
        for leg in route["legs"]:
            distance += leg["distance"]["value"]
        item["distance"] = distance # meters
        changed = True
    if "duration" not in item:
        duration = 0
        for leg in route["legs"]:
            duration += leg["duration"]["value"]
        item["duration"] = duration # seconds
        changed = True
        pass
    return changed

def load_route(addresses=None, route_id=None):
    if (not not addresses) == (not not route_id):
        raise RuntimeError("Must provide one and only one of addresses and route_id!")
    if addresses:
        route_id = get_route_id(addresses)
        item = load_route_from_db(route_id)
        if item:
            print("Route {} loaded from database.".format(route_id))
            if ensure_all_fields_filled(item):
                print("Route entry contents updated.  Updating database.")
                ROUTE_TABLE.put_item(Item=item)
        else:
            print("Loading route {} from google maps.".format(route_id))
            route = load_route_from_google(addresses)
            item = {
                "route_id":route_id,
                "route":json.dumps(route, separators=(',',':'))
            }
            ensure_all_fields_filled(item)
            ROUTE_TABLE.put_item(Item=item)
            print("Route {} loaded from google maps and cached.".format(route_id))
    else:
        item = load_route_from_db(route_id)
        if ensure_all_fields_filled(item):
            print("Route entry contents updated.  Updating database.")
            ROUTE_TABLE.put_item(Item=item)
        if not item:
            return route_id, None, None
    return route_id, convert_python_route_to_javascript(item["route"]), item

def load_team_from_db(team_id):
    try:
        item = TEAM_TABLE.get_item(Key={"team_id":team_id})["Item"]
        return item
    except:
        traceback.print_exc()
    return None

def get_team_id():
    uuid = str(uuid.uuid1()).replace('-','').lower()
    return uuid

def load_team(team_id=None):
    team_id = team_id if team_id else get_team_id()
    item = load_team_from_db(team_id)
    if item:
        print("Team {} loaded from database.".format(team_id))
    else:
        print("Creating new team {}.".format(team_id))
        item = {
            "team_id":team_id,
        }
        TEAM_TABLE.put_item(Item=item)
    item = deepload(item)
    return item
