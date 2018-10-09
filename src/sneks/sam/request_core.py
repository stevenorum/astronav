import http.cookies
import json
import os
import urllib.parse
import traceback
from functools import update_wrapper

def listify(obj):
    if obj == None:
        return []
    if isinstance(obj, (list,tuple)):
        return obj
    return [obj]

def unlistify(obj):
    if obj == None:
        return None
    if isinstance(obj, (list,tuple)):
        if len(obj) == 0:
            return None
        elif len(obj) == 1:
            return obj[0]
    return obj

def listify_dict(d):
    keys = list(d.keys())
    new_d = dict()
    for k in keys:
        new_d[k] = listify(d[k])
    return new_d

def unlistify_dict(d):
    keys = list(d.keys())
    new_d = dict()
    for k in keys:
        new_d[k] = unlistify(d[k])
    return new_d

def dict_append(d, k, v):
    # d = listify_dict(d)
    d[k] = listify(d.get(k,[]))
    d[k].extend(listify(v))
    return d

def update_lists(d1, d2):
    # d1 = listify_dict(d1)
    # d2 = listify_dict(d2)
    for k in d2:
        d1[k] = listify(d1.get(k,[]))
        d1 = dict_append(d1, k, d2[k])
    return d1

def parse_body(body):
    if body.startswith("{"):
        try:
            return json.loads(body)
        except:
            traceback.print_exc()
    else:
        try:
            return urllib.parse.parse_qs(body)
        except:
            traceback.print_exc()
    return {}

def add_event_params(event, *args, **kwargs):
    params = {}
    event["queryStringParameters"] = event.get("queryStringParameters") if event.get("queryStringParameters") else {}
    params.update(event["queryStringParameters"])
    if event["httpMethod"] == "POST" and event.get("body"):
        body = event["body"]
        update_lists(params, parse_body(body))
    cookie_dict = {}
    try:
        cookies = http.cookies.SimpleCookie()
        cookies.load(event["headers"].get("Cookie",""))
        for k in cookies:
            morsel = cookies[k]
            cookie_dict[morsel.key] = morsel.value
    except:
        traceback.print_exc()
    params = listify_dict(params)
    params = {"kwargs":params}
    params["single_kwargs"] = unlistify_dict(params["kwargs"])
    params["cookies"] = cookie_dict
    params["path"] = {}
    params["path"]["raw"] = event["path"]
    params["path"]["base"] = event["requestContext"]["path"][:-1*len(event["path"])].rstrip("/")
    params["path"]["full"] = "https://" + event["headers"]["Host"] + params["path"]["raw"]
    params["path"]["full_base"] = "https://" + event["headers"]["Host"] + params["path"]["base"]
    if "STATIC_BUCKET" in os.environ and "STATIC_PATH" in os.environ:
        params["path"]["static_base"] = "https://s3.amazonaws.com/{STATIC_BUCKET}/{STATIC_PATH}".format(**os.environ)
    else:
        params["path"]["static_base"] = params["path"]["base"]
    params["http"] = {}
    params["http"]["Referer"] = event.get("headers",{}).get("Referer","")
    params["http"]["Referer"] = params["http"]["Referer"] if params["http"]["Referer"] else params["path"]["full_base"]
    params["http"]["User-Agent"] = event.get("headers",{}).get("User-Agent")
    params["http"]["Method"] = event["httpMethod"]
    params["redirect"] = params["single_kwargs"].get("redirect", params["http"]["Referer"])
    params["redirect"] = params["redirect"] if params["redirect"] else params["path"]["full_base"]
    params["objects"] = {}
    event["params"] = params
    return event

def event_params_decorator(func):
    def newfunc(event, *args, **kwargs):
        event = add_event_params(event)
        return func(event, *args, **kwargs)
    update_wrapper(newfunc, func)
    return newfunc
