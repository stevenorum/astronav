import copy
import json
import re
from urllib.parse import urlencode, urlparse, parse_qs

def make_response(body, code=200, headers={}, base64=False):
    _headers = {"Content-Type": "text/html"}
    if isinstance(body, (list,dict)):
        body = json.dumps(body)
        _headers = {"Content-Type": "application/json"}
    _headers.update(headers)
    return {
        "body": body,
        "statusCode": code,
        "headers": _headers,
        "isBase64Encoded": base64
    }

def redirect(target_url, temporary=True, headers={}, qs={}):
    print("Redirecting to {} with additional qs {}".format(target_url, qs))
    if qs:
        parsed = urlparse(target_url)
        eqs = parse_qs(parsed.query)
        newqs = set()
        for k in eqs:
            for e in eqs[k]:
                newqs.add(urlencode({k:e}))
        for k in qs:
            newqs.add(urlencode({k:qs[k]}))
        full_qs = "&".join(list(newqs))
        target_url = parsed.netloc + parsed.path
        if parsed.scheme:
            target_url = parsed.scheme + "://" + target_url
        if parsed.params:
            target_url += ";" + parsed.params
        if full_qs:
            target_url += "?" + full_qs
        if parsed.fragment:
            target_url += "#" + parsed.fragment
    _headers = {"Location": target_url}
    _headers.update(headers)
    print("Redirect headers: {}".format(_headers))
    return make_response(
        body = "",
        code = 303 if temporary else 301,
        headers = _headers
    )

class EventMatcher(object):
    def __init__(self, response_function, default_kwargs={}, matcher_function=None, preprocessor_functions=[]):
        self.response_function = response_function
        self.kwargs = default_kwargs
        preprocessor_functions = preprocessor_functions if isinstance(preprocessor_functions, (list, tuple)) else [preprocessor_functions]
        self.preprocessor_functions = preprocessor_functions if preprocessor_functions else getattr(self, "preprocessor_functions", [])
        self.matcher_function = matcher_function if matcher_function else getattr(self, "matcher_function", lambda *args, **kwargs: (False,None))

    def match_event(self, event):
        resp = self.matcher_function(event)
        if len(resp) != 2 or not resp[0]:
            return None, None
        kwargs = copy.deepcopy(self.kwargs)
        kwargs.update(resp[1])
        kwargs["event"] = event if "event" not in kwargs else kwargs.get("event")
        for processor_func in self.preprocessor_functions:
            kwargs = processor_func(kwargs)
        return (self.response_function, kwargs)

    def handle_event(self, event):
        match = self.match_event(event)
        if match and match[0]:
            function = match[0]
            kwargs = match[1]
            return function(**kwargs)
        return None

class PathMatcher(EventMatcher):
    def __init__(self, regex, function, default_kwargs={}, preprocessor_functions=[]):
        super().__init__(function, default_kwargs, preprocessor_functions=preprocessor_functions)
        self.matcher = re.compile(regex)

    def matcher_function(self, event):
        path = event.get("path")
        response = self.matcher.match(path)
        if response:
            return (True, response.groupdict())
        return False, None

class ListMatcher(EventMatcher):
    def __init__(self, matchers):
        self.matchers = matchers

    def match_event(self, event):
        for matcher in self.matchers:
            resp = matcher.match_event(event)
            if resp[0]:
                return resp
        return None, None

class ResponseException(Exception):
    def __init__(self, response):
        self.response = response

class ApiException(ResponseException):
    def __init__(self, data={}, code=500):
        self.response = make_response(body=data, code=code)
