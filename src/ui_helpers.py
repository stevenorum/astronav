import base64
import json
import os
import traceback
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("/var/task/jinja_templates/"))

try:
    with open("/var/task/static_config.json") as f:
        data = json.load(f)
        for k in data:
            os.environ[k] = data[k].strip()
except:
    traceback.print_exc()
    print("Unable to add static info to the path.  Falling back to the bundled defaults.")

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

def make_response(body, code=200, headers={"Content-Type": "text/html"}, is_base64=False):
    return {
        "body": body,
        "statusCode": code,
        "headers": headers,
        "isBase64Encoded": is_base64
    }

def render_page(name, params={}, code=200, headers={}):
    params = params if params else {}
    headers = headers if headers else {}

    template = env.get_template(name)
    body = template.render(**params)
    _headers = {"Content-Type": get_content_type(name)}
    _headers.update(headers)
    return make_response(body=body, code=code, headers=_headers, is_base64=False)

def get_static(filename, event=None, **kwargs):
    if "STATIC_BUCKET" in os.environ and "STATIC_PATH" in os.environ:
        return make_response(body="", code=303, headers={"Location":"https://s3.amazonaws.com/{STATIC_BUCKET}/{STATIC_PATH}/{filename}".format(filename=filename, **os.environ)})
    filepath = os.path.abspath(os.path.join("/var/task",filename))
    if os.path.isfile(filepath) and filepath.startswith("/var/task/static/"):
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
