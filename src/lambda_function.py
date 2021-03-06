import handlers

from sneks.sam.response_core import PathMatcher, ListMatcher, ResponseException
from sneks.sam import ui_stuff

STATIC_MATCHERS = [
    PathMatcher(r"^.*/?favicon.ico$", ui_stuff.get_static, {"filename":"static/favicon.ico"}),
    PathMatcher(r"^/?(?P<filename>static/.*)$", ui_stuff.get_static),
]

STANDARD_PREPROCESSORS = [
]

DYNAMIC_MATCHERS = [
    PathMatcher(r"^/?$", ui_stuff.get_page, {"template_name":"index.html"}, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?store_route$", handlers.store_route, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?route_map.html$", handlers.view_route, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?new_route.html$", handlers.new_route_handler, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?route_list.html$", handlers.route_list_handler, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?all_routes.html$", handlers.route_list_all_handler, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r"^/?(?P<template_name>[a-z_]*.html)$", ui_stuff.get_page, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r".*debug.*", ui_stuff.make_debug, preprocessor_functions=STANDARD_PREPROCESSORS),
    PathMatcher(r".*", ui_stuff.make_404),
]

MATCHERS = ListMatcher(STATIC_MATCHERS + DYNAMIC_MATCHERS)

def lambda_handler(event, context):
    try:
        return MATCHERS.handle_event(event)
    except ResponseException as e:
        return e.response
