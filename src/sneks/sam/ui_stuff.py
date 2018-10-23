import base64
import json
import os
from functools import update_wrapper
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound
from sneks.sam.response_core import make_response, redirect, ResponseException
from sneks.sam import events
from sneks import snekjson
import traceback

env = Environment(loader=FileSystemLoader(os.path.join(os.environ["LAMBDA_TASK_ROOT"], "jinja_templates")))

conf_files = ["static_config.json", "extra_params.json"]
for filename in conf_files:
    try:
        with open(os.path.join(os.environ["LAMBDA_TASK_ROOT"], filename)) as f:
            data = json.load(f)
            for k in data:
                os.environ[k] = data[k].strip()
    except:
        traceback.print_exc()
        print("Unable to load configuration file '{}'".format(filename))

content_types = {
    "ico":"image/x-icon",
    "jpg":"image/jpg",
    "jpeg":"image/jpeg",
    "png":"image/png",
    "gif":"image/gif",
    "bmp":"image/bmp",
    "tiff":"image/tiff",
    "txt":"text/plain",
    "rtf":"application/rtf",
    "ttf":"font/ttf",
    "css":"text/css",
    "html":"text/html",
    "js":"application/javascript",
    "eot":"application/vnd.ms-fontobject",
    "svg":"image/svg+xml",
    "woff":"application/x-font-woff",
    "woff2":"application/x-font-woff",
    "otf":"application/x-font-otf",
    "json":"application/json",
    }

binary_types = [
    "image/jpg",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/x-icon",
    "font/ttf",
    "application/vnd.ms-fontobject",
    "application/x-font-woff",
    "application/x-font-otf",
]

def get_content_type(fname, body=None):
    return content_types.get(fname.split(".")[-1].lower(),"binary/octet-stream")

def get_params(template_name, event=None, **kwargs):
    params = {}
    params["this_page"] = template_name
    if event:
        params["event"] = event
        params["base_path"] = events.base_path(event)
        params["static_base"] = events.static_path(event)
    params.update(kwargs)
    return snekjson.blob(params)

def get_page(template_name, event=None, **kwargs):
    try:
        return make_response(env.get_template(template_name).render(**get_params(template_name, event, this_page=template_name, **kwargs)))
    except TemplateNotFound as e:
        traceback.print_exc()
        print(e)
        print(dir(e))
        print(vars(e))
        return make_404(event)

def render_page(name, params={}, code=200, headers={}):
    params = params if params else {}
    headers = headers if headers else {}

    template = env.get_template(name)
    body = template.render(**params)
    _headers = {"Content-Type": get_content_type(name)}
    _headers.update(headers)
    return make_response(body=body, code=code, headers=_headers, is_base64=False)

def is_response(d):
    return len(d) == 4 and "body" in d and "statusCode" in d and "headers" in d and "isBase64Encoded" in d

def loader_for(template_name):
    def new_decorator(func):
        def newfunc(event, *args, **kwargs):
            params = func(event, *args, **kwargs)
            if is_response(params):
                return params
            return get_page(template_name, event, **params)
        update_wrapper(newfunc, func)
        return newfunc
    return new_decorator

def make_message(message, heading="Example Website", event=None, **kwargs):
    template_name = "message.html.jinja"
    body = env.get_template(template_name).render(message_title=heading, message_html=message, **get_params(template_name, event))
    return make_response(body, **kwargs)

def get_static(filename, event=None, **kwargs):
    if "STATIC_BUCKET" in os.environ and "STATIC_PATH" in os.environ:
        return redirect("https://s3.amazonaws.com/{STATIC_BUCKET}/{STATIC_PATH}/{filename}".format(filename=filename, **os.environ))
    filepath = os.path.abspath(os.path.join(os.environ["LAMBDA_TASK_ROOT"],filename))
    if os.path.isfile(filepath) and filepath.startswith(os.path.join(os.environ["LAMBDA_TASK_ROOT"],"static","")):
        content_type = get_content_type(filename)
        b64encoded = False
        if content_type in binary_types:
            with open(filepath,"rb") as f:
                body = base64.b64encode(f.read()).decode("utf-8")
                b64encoded = True
        else:
            with open(filepath,"r") as f:
                body = f.read()
        return make_response(body=body, headers={"Content-Type": content_type}, base64=b64encoded)
    else:
        return make_response("404!!1!", code=404)

def get_debug_blob(event):
    templates = env.list_templates()
    return "<pre>\n{}\n\nAvailable Jinja2 templates:\n\n{}\n</pre>".format(snekjson.dumps(event, indent=2, sort_keys=True, ignore_type_error=True).replace(">","&gt").replace("<","&lt"),"\n".join(templates))

def make_debug(event=None, context=None, headers={}, **kwargs):
    templates = env.list_templates()
    return make_response(body=get_debug_blob(event), headers=headers)

def make_404(event=None, context=None, **kwargs):
    raise ResponseException(make_message("<p>I have no idea what you're talking about.</p><br><br><p>{}</p>".format(get_debug_blob(event)), event=event, heading="HTTP/404 !!1!", code=404))
