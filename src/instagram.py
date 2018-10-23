#!/usr/bin/env python3

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import requests

def profile_url(name):
    return "https://www.instagram.com/{}/".format(name)

def image_url(shortcode):
    return "https://www.instagram.com/p/{}/".format(shortcode)

def get_page_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    for x in soup.find_all('script'):
        # Janky but it works.
        # That should probably just be my motto at this point.
        if x.contents and 'window._sharedData =' in x.contents[0]:
            datastring = x.contents[0].replace('window._sharedData = ','')[:-1]
            return json.loads(datastring)
    return {}

def get_images_from_profile(name="teamslothgoruck"):
    response = requests.get(profile_url(name))
    data = get_page_data(response.text)
    edges = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]
    nodes = [e.get("node") for e in edges if e.get("node") and e["node"].get("__typename")=="GraphImage"]
    shortcodes = [n["shortcode"] for n in nodes]
    return shortcodes

def get_image_info(shortcode):
    info = {
        "shortcode":shortcode,
        "caption":None,
        "street_address":None,
        "city_name":None,
        "zip_code":None,
        "location_name":None,
        "coordinates":None,
        "timestamp":None,
    }
    response = requests.get(image_url(shortcode))
    imgdata = get_page_data(response.text)["entry_data"]["PostPage"][0]["graphql"]["shortcode_media"]
    info["timestamp"] = imgdata.get("taken_at_timestamp")
    caption_edges = imgdata["edge_media_to_caption"]["edges"]
    if caption_edges:
        info["caption"] = caption_edges[0]["node"]["text"]
    location = imgdata["location"] if imgdata["location"] else {}
    info["location_name"] = location.get("name")
    info["sizes"] = imgdata.get("display_resources",[])
    address_json = location.get("address_json")
    if address_json:
        address = json.loads(address_json)
        for piece in ["street_address", "city_name", "zip_code"]:
            info[piece] = address.get(piece)
    return info

