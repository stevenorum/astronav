import json

from ui_stuff import loader_for

# @loader_for("route.html")
@loader_for("message.html")
def submit_waypoints(event, context):
    params = {
        "message_title":"Waypoints:",
        "message_html":"<pre>{}</pre>".format(json.dumps(event))
    }
    return params
