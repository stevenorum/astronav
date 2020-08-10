import base64
import boto3
import copy
from datetime import datetime, timedelta
from decimal import Decimal
import gmaps
import hashlib
import http.cookies
import json
from math import radians, degrees, cos, sin, asin, sqrt, fabs, log, tan, pi, atan2
import os
import traceback
import urllib
import urllib.parse
import uuid
from sneks.sam import events
from sneks.sam.response_core import make_response, redirect, ApiException
from sneks.sam.ui_stuff import loader_for, make_404
import time

ROUTE_TABLE = boto3.resource("dynamodb").Table(os.environ["ROUTE_TABLE"])

def make_json_safe(item):
    if isinstance(item, list):
        item = [make_json_safe(e) for e in item]
    if isinstance(item, dict):
        item = {k:make_json_safe(item[k]) for k in item}
    if isinstance(item, Decimal):
        item = float(item)
    return item

def dumps(obj, *args, **kwargs):
    return json.dumps(make_json_safe(obj), *args, **kwargs)

def make_ddb_safe(item):
    if isinstance(item, list):
        item = [make_ddb_safe(e) for e in item]
    elif isinstance(item, dict):
        item = {k:make_ddb_safe(item[k]) for k in item}
    elif isinstance(item, float):
        item = Decimal(item)
    elif item is None:
        item = "null"
    elif item == "":
        item = json.dumps("")
    elif isinstance(item, str):
        pass
    elif isinstance(item, int):
        pass
    else:
        print(item)
    return item

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

def ddb_save(table, item, **kwargs):
    item = make_ddb_safe(item)
    try:
        table.put_item(Item=item, **kwargs)
    except:
        print("Error saving the following object:")
        print(dumps(item))
        traceback.print_exc()
        raise

def save_route(item, **kwargs):
    ddb_save(ROUTE_TABLE, item, **kwargs)

def store_route(event, *args, **kwargs):
    body = deepload(event["body"])
    superoptimize = body.get("superoptimize", False)
    if "addresses" in body:
        route_id, response, item = load_route(addresses=body["addresses"], superoptimize=superoptimize)
    elif "route_id" in body:
        route_id, response, item = load_route(route_id=body["route_id"])
    else:
        return make_404(event)
    if not response:
        return make_404(event)
    return make_response({"redirect":events.base_path(event) + "/route_map.html?route_id={}".format(route_id)})

def add_created(route):
    dt = datetime.fromtimestamp(route["created"])
    dt_string = dt.strftime("%Y/%m/%d %H:%M:%S")
    route["created_string"] = dt_string
    return route

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
        "GMAPS_API_KEY":os.environ["GMAPS_PUBLIC"],
        "route_id":route_id,
        "js_data":dumps(response, sort_keys=True, separators=(',',':')),
        "distance":format_distance(item["distance"]),
        "duration":format_time(item["duration"]),
        "addresses":item["addresses"],
        "superoptimize":item.get("superoptimize", False),
        "addresses_for_copy":base64.urlsafe_b64encode(json.dumps(item["addresses"]).encode("utf-8")).decode("utf-8")
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

@loader_for("new_route.html")
def new_route_handler(event, *args, **kwargs):
    params = event.get("multiValueQueryStringParameters",{})
    params = params if params else {}
    addresses = params.get("addresses",[])
    response = {"return_to_start":True}
    if addresses:
        addresses = json.loads(base64.urlsafe_b64decode(addresses[0].encode("utf-8")).decode("utf-8"))
    if addresses:
        if addresses[0] == addresses[-1]:
            addresses = addresses[:-1]
        else:
            response["return_to_start"] = False
        response["addresses"] = "\n".join(addresses)
    return response

@loader_for("route_list.html")
def route_list_handler(event, *args, **kwargs):
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
        add_created(route)
        route["addresses"] = deepload(route["addresses"])
        route["num_locations"] = len(route["addresses"])
        route["distance"] = format_distance(route.get("distance")) if route.get("distance") else "???"
        route["duration"] = format_time(route.get("duration")) if route.get("duration") else "???"
    return {"routes":routes,"last_route":new_last_route}

@loader_for("route_list.html")
def route_list_all_handler(event, *args, **kwargs):
    all_routes = []
    last_route = None
    all_routes, last_route = list_routes(last_route=last_route)
    while last_route:
        routes, last_route = list_routes(last_route=last_route)
        all_routes.extend(routes)
    routes = [r for r in all_routes if r.get("addresses")]
    routes.sort(key=lambda x: x.get("created",0), reverse=True)
    for route in routes:
        add_created(route)
        route["addresses"] = deepload(route["addresses"])
        route["num_locations"] = len(route["addresses"])
        route["distance"] = format_distance(route.get("distance")) if route.get("distance") else "???"
        route["duration"] = format_time(route.get("duration")) if route.get("duration") else "???"
    return {"routes":routes,"this_page_":"all_routes.html"}

def list_routes(last_route=None):
    kwargs = {
        "Select":"SPECIFIC_ATTRIBUTES",
        "ProjectionExpression":"#RID, #ADR, #DUR, #DIS, #CRE, #NAM, #SUP",
        "ExpressionAttributeNames":{
            "#RID":"route_id",
            "#ADR":"addresses",
            "#DUR":"duration",
            "#DIS":"distance",
            "#CRE":"created",
            "#NAM":"name",
            "#SUP":"superoptimize"
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
        if item.get("route") and gmaps.convert_python_route_to_javascript(deepload(item["route"])):
            # Make sure it contains a result and that the result can be parsed.
            return item
    except:
        traceback.print_exc()
    return None

def get_route_id(addresses, superoptimize=False):
    if superoptimize:
        route_id = hashlib.md5("\n".join([a.strip().lower() for a in addresses]).encode("utf-8")).hexdigest()
    else:
        route_id = hashlib.md5("\n".join([a.strip().upper() for a in addresses]).encode("utf-8")).hexdigest()
    return route_id

def ensure_route_fields_filled(item):
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
        # Assumes 15 minutes per mile.
        # Old method no longer works because some legs assume driving or bicycling
        item["duration"] = int(item["distance"] / 1609.34 * 900)
        changed = True
        pass
    if "created" not in item:
        item["created"] = int(time.time())
        changed = True
    if "description" not in item:
        if item["created"] == 1539997200:
            item["description"] = "(Note: creation time was backfilled and was sometime between that time and October 23rd.)"
        else:
            item["description"] = ""
        changed = True
    if "superoptimize" not in item:
        item["superoptimize"] = False
        changed = True
    return changed

def load_route(addresses=None, route_id=None, superoptimize=False):
    if (not not addresses) == (not not route_id):
        raise RuntimeError("Must provide one and only one of addresses and route_id!")
    if addresses:
        route_id = get_route_id(addresses, superoptimize=superoptimize)
        item = load_route_from_db(route_id)
        if item:
            print("Route {} loaded from database.".format(route_id))
            if ensure_route_fields_filled(item):
                print("Route entry contents updated.  Updating database.")
                save_route(item)
        else:
            print("Loading route {} from google maps.".format(route_id))
            try:
                route = gmaps.load_route_from_google(addresses, superoptimize=superoptimize)
            except:
                if 'MAX_ROUTE_LENGTH_EXCEEDED' in traceback.format_exc():
                    raise ApiException(data={"message":"Requested route too long.  Perhaps you need to specify cities/states for each address?"}, code=400)
                elif 'MAX_WAYPOINTS_EXCEEDED' in traceback.format_exc():
                    raise ApiException(data={"message":"Too many waypoints specified.  The maximum is 25, counting the start and end points."}, code=400)
                raise
            item = {
                "route_id":route_id,
                "route":dumps(route, separators=(',',':')),
                "created":int(time.time()),
                "superoptimize":superoptimize
            }
            ensure_route_fields_filled(item)
            try:
                save_route(item)
            except:
                if 'Item size has exceeded the maximum allowed size' in traceback.format_exc():
                    raise ApiException(data={"message":"Requested route's directions are too big.  Perhaps you need to specify cities/states for each address?"}, code=400)
            print("Route {} loaded from google maps and cached.".format(route_id))
    else:
        item = load_route_from_db(route_id)
        if ensure_route_fields_filled(item):
            print("Route entry contents updated.  Updating database.")
            save_route(item)
        if not item:
            return route_id, None, None
    return route_id, gmaps.convert_python_route_to_javascript(deepload(item["route"])), item

def get_cookies(event):
    cookie_dict = {}
    try:
        cookies = http.cookies.SimpleCookie()
        cookies.load(event["headers"].get("Cookie",""))
        for k in cookies:
            morsel = cookies[k]
            cookie_dict[morsel.key] = morsel.value
    except:
        traceback.print_exc()
    return cookie_dict
