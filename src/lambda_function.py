import json

from sneks.sam.response_core import PathMatcher, ListMatcher

from sneks.sam import ui_stuff

STATIC_MATCHERS = [
    PathMatcher(r"^.*/favicon.ico$", ui_stuff.get_static, {"filename":"static/favicon.ico"}),
    PathMatcher(r"^/?(?P<filename>static/.*)$", ui_stuff.get_static),
]

DYNAMIC_MATCHERS = [
    PathMatcher(r"^/?$", ui_stuff.get_page, {"template_name":"index.html"}),
    PathMatcher(r"^/?(?P<template_name>[a-z_]*.html)$", ui_stuff.get_page),
    PathMatcher(r".*debug.*", ui_stuff.make_debug),
    PathMatcher(r".*", ui_stuff.make_404),
]

MATCHERS = ListMatcher(STATIC_MATCHERS + DYNAMIC_MATCHERS)

def lambda_handler(event, context):
    return MATCHERS.handle_event(event)
