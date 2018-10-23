import json

import handlers

from sneks.sam.response_core import PathMatcher, ListMatcher
from sneks.sam import ui_stuff

STATIC_MATCHERS = [
    PathMatcher(r"^.*/favicon.ico$", ui_stuff.get_static, {"filename":"static/favicon.ico"}),
    PathMatcher(r"^/?(?P<filename>static/.*)$", ui_stuff.get_static),
]

STANDARD_PREPROCESSORS = [
    handlers.add_team_to_event
]

DYNAMIC_MATCHERS = [
    PathMatcher(r"^/?$", ui_stuff.get_page, {"template_name":"index.html"}, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?store_route$", handlers.store_route, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?team_login$", handlers.team_login, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?route_map.html$", handlers.view_route, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?new_route.html$", handlers.new_route_handler, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?route_list.html$", handlers.route_list_handler, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?team_images.html$", handlers.team_images_handler, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?(?P<template_name>[a-z_]*.html)$", ui_stuff.get_page, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r".*debug.*", ui_stuff.make_debug, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r".*", ui_stuff.make_404),
]

MATCHERS = ListMatcher(STATIC_MATCHERS + DYNAMIC_MATCHERS)

def lambda_handler(event, context):
    return MATCHERS.handle_event(event)
