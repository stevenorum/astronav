function getPointsToDisplay() {
    if (gpxs.trk.length > 0) {
        var points_to_return = [];
        //        console.log("gpxs.trk.length: " + gpxs.trk.length);
        for (var i = 0; i < gpxs.trk.length; i++) {
            //  console.log("Adding points from track " + i + " to the array of arrays.");
            points_to_return.push(getPointsFromTrack(gpxs.trk[i]));
        }
        return points_to_return;
    }
    else if (gpxs.wpt.length > 0) {
        return [gpxs.wpt];
    }
    else return [[]];
}

function get_timestamp(time) {
    full_timestamp = new Date(time).getTime();
    return full_timestamp / 1000;
}

function match_times() {
    return document.getElementById("standardize_times").checked;
}

function auto_scroll() {
    return document.getElementById("auto_scroll").checked;
}

function get_track_color(track_number) {
    var colors = ["FF0000","FFFF00","00FF00","00FFFF","0000FF","FF00FF"];
    return colors[track_number % colors.length];
}

function format_timestamp(timestamp) {
    var sec_num = parseInt(timestamp, 10); // don't forget the second param
    var hours   = Math.floor(sec_num / 3600);
    var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
    var seconds = sec_num - (hours * 3600) - (minutes * 60);

    if (hours   < 10) {hours   = "0"+hours;}
    if (minutes < 10) {minutes = "0"+minutes;}
    if (seconds < 10) {seconds = "0"+seconds;}
    var time    = hours+':'+minutes+':'+seconds;
    return time;
}

function addMarkers() {
    for (var i = 0; i < points.length; i++){
        console.log("Adding markers for points in track " + i);
        for (var j = 0; j < points[i].length; j++){
            points[i][j].marker = getMarker(points[i][j].lat, points[i][j].lon, get_track_color(i));
        }
    }
}

function getClosestIndex(timestamp, track_num, first_index, last_index) {
    console.log("getClosestIndex called with inputs: " + timestamp + ", " + track_num + ", " + first_index + ", " + last_index);
    if (first_index == last_index) {

        return first_index;
    }
    if (first_index + 1 == last_index) {
        first_gap = timestamp - get_timestamp(points[track_num][first_index].time);
        last_gap = get_timestamp(points[track_num][last_index].time) - timestamp;
        if (first_gap < last_gap) {return first_index;}
        else {return last_index;}
    }
    halfway = Math.round((first_index + last_index)/2);
    halfway_timestamp = get_timestamp(points[track_num][halfway].time);
    if (halfway_timestamp > timestamp) {
        return getClosestIndex(timestamp, track_num, first_index, halfway);
    } else if (halfway_timestamp < timestamp) {
        return getClosestIndex(timestamp, track_num, halfway, last_index);
    } else {
        return halfway;
    }
}

function getMarker(lat, lon, color) {
    var pinImage = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|" + color,
                                               new google.maps.Size(21, 34),
                                               new google.maps.Point(0,0),
                                               new google.maps.Point(10, 34));
    var pinShadow = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_shadow",
                                                new google.maps.Size(40, 37),
                                                new google.maps.Point(0, 0),
                                                new google.maps.Point(12, 35));
    var marker = new google.maps.Marker({
            position: new google.maps.LatLng(lat,lon),
            map: map,
            icon: pinImage,
            shadow: pinShadow
        });
    return marker;
}

function hideAllPoints() {
    // hide all old points - I need to figure out how to fully delete them easily
    for (i = 0; i<visible_points.length; i++){
        while (visible_points[i].length > 0) {
            visible_points[i].pop().marker.setVisible(false);
        }
    }
}

function setStartAndEndTimes() {
    track_start_times = [];
    track_end_times = [];
    for (var i = 0; i < points.length; i++) {
        if (points[i].length > 0) {
            if (points[i][0].time != null) {
                track_start_times.push(points[i][0].time);
                if (startTime == null) {
                    startTime = points[i][0].time;
                } else if (startTime > points[i][0].time) {
                    startTime = points[i][0].time;
                }
            } else {track_start_times.push(null);}
            var last = points[i].length-1;
            if (points[i][last].time != null) {
                track_end_times.push(points[i][last].time);
                if (endTime == null) {
                    endTime = points[i][last].time;
                } else if (endTime < points[i][last].time) {
                    endTime = points[i][last].time;
                }
            } else {track_end_times.push(null);}
        }
    }

    var total_duration = get_timestamp(endTime) - get_timestamp(startTime);

    console.log("Start time: " + startTime);
    console.log("End time:   " + endTime);
    for (var i = 0; i < points.length; i++) {
        var duration = get_timestamp(track_end_times[i]) - get_timestamp(track_start_times[i]);
        if (duration > max_track_duration) {max_track_duration = duration;}
        console.log("Start time for track " + i + ": " + track_start_times[i]);
        console.log("End time for track " + i + ":   " + track_end_times[i]);
        console.log("Offset for track " + i + ":     " + track_offsets[i]);
    }
}

function loadPoints() {
    hideAllPoints();
    var gpx_text = document.getElementById('gpx_input').value;
    var gpx_xml_doc = $.parseXML(gpx_text);

    gpxs = loadGpx(gpx_xml_doc);
    points = getPointsToDisplay();
    for (var i = 0; i < points.length; i++) {
        visible_points.push([]);
    }
    document.getElementById('number_of_tracks').innerHTML = "Number of tracks: " + points.length;
    setStartAndEndTimes();
    addMarkers();
    if (points[0].length > 0) {
        var center = new google.maps.LatLng(points[0][0].lat, points[0][0].lon);
    }
    else {
        var center = new google.maps.LatLng(39.246712, -106.291143);
    }
    map.setCenter(center);
    loadSlider();
    showPoints();
    move_slider_to(get_slider_start_value());
}

function getPointsFromTrack(track) {
    var point_list = [];
    for (i = 0; i < track.trkseg.length; i=i+1) {
        for (j = 0; j < track.trkseg[i].trkpt.length; j=j+1) {
            point_list.push(track.trkseg[i].trkpt[j]);
        }
    }
    return point_list;
}

function showPoints() {
    for (i = 0; i < points.length; i++) {
        for (j=0;j<points[i].length;j++){
            visible_points[i].push(points[i][j]);
            points[i][j].marker.setVisible(true);
        }
    }
}

function format_timestamp_for_display(timestamp) {
    var rep = ":" + timestamp%60;
    rep = Math.floor(timestamp/60)%60 + rep;
    rep = Math.floor(timestamp/3600)%24 + ":" + rep;
    rep = Math.floor(timestamp/86400) + ":" + rep;
    return rep;
}

function slider_moved_to(timestamp) {
    console.log("Finding point for timestamp " + timestamp + ", standardized.");
    if (match_times()) {
        document.getElementById('time_display').innerHTML = "Time: " + format_timestamp(timestamp);
    } else {
        document.getElementById('time_display').innerHTML = "Time: " + format_timestamp(timestamp - get_timestamp(startTime));
    }

    for (var i = 0; i < points.length; i++){
        var endex = Math.max(points[i].length - 1, 0);
        if (match_times()) {
            var index = getClosestIndex(timestamp + get_timestamp(track_start_times[i]), i, 0, endex);
        } else {
            var index = getClosestIndex(timestamp, i, 0, endex);
        }
        console.log("Index for track " + i + ": " + index);

        while (visible_points[i].length > 0) {
            visible_points[i].pop().marker.setVisible(false);
        }
        if (points[i][index] != null) {
            visible_points[i].push(points[i][index]);
            points[i][index].marker.setVisible(true);
        }
    }
}

function move_slider_to(value) {
    $( "#slider" ).slider("value", value);
    slider_moved_to(value);
}

function get_slider_start_value() {
    if (match_times()) {
        return 0;
    } else {
        return get_timestamp(startTime);
    }
}

function get_slider_end_value() {
    if (match_times()) {
        return max_track_duration;
    } else {
        return get_timestamp(endTime);
    }
}

function loadSlider() {
    var start = get_slider_start_value();
    var end = get_slider_end_value();
    $(function() {
            $( "#slider" ).slider({ min: start, max: end});
        });
    $( "#slider" ).on("slide",function( event, ui ) {
            slider_moved_to(ui.value);
        });

    move_slider_to(start);

    var myVar=setInterval(function(){slide_timer()},50);

    function slide_timer()
    {
        if(auto_scroll()) {
            var next_value = $( "#slider" ).slider("value") + 1;
            move_slider_to(next_value);
        }
    }
}

function autoScrollClicked() {
}

function initialize() {
    map = new google.maps.Map(document.getElementById('map-canvas')); // the map
    gpxs = new gpx(); // the current gpx object
    points = [[]]; // the current points
    startTime = null;
    endTime = null;
    track_start_times = [];
    track_end_times = [];
    track_offsets = [];
    total_duration = 0;
    max_track_duration = 0;
    visible_points = [];
    loadPoints();

    map.setZoom(14);

    document.getElementById("loadPoints").onclick = loadPoints;
    document.getElementById("showPoints").onclick = showPoints;
    document.getElementById("standardize_times").onclick = loadSlider;
    document.getElementById("auto_scroll").onclick = autoScrollClicked;
}

google.maps.event.addDomListener(window, 'load', initialize);
