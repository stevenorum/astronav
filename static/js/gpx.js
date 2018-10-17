// object model

function bounds(minlat, minlon, maxlat, maxlon)
{
    this.minlat = minlat;
    this.minlon = minlon;
    this.maxlat = maxlat;
    this.maxlon = maxlon;
}

function metadata()
{
    this.name = null;
    this.desc = null;
    this.copyright = null;
    this.time = null;
    this.links = [];
    this.keywords = null;
    this.bounds = null;
    this.extensions = null;
}

function wpt(latitude, longitude)
{
    this.lat = latitude;
    this.lon = longitude;
    this.ele = 0;
    this.time = null;
    this.magvar = 0;
    this.geoidheight = 0;
    this.name = null;
    this.cmt = null;
    this.desc = null;
    this.src =null;
    this.link = [];
    this.sym = null;
    this.type = null;
    this.fix = null;
    this.sat = 0;
    this.hdop = 0;
    this.vdop = 0;
    this.pdop = 0;
    this.ageofdgpsdata = 0;
    this.dgpsid = null;
    this.extensions = null;
    this.marker = null;
}

function rte() {
    this.name = null;
    this.cmt = null;
    this.desc = null;
    this.src = null;
    this.link = [];
    this.number = 0;
    this.type = null;
    this.extensions = null;
    this.rtept = [];
}

function trk() {
    this.name = null;
    this.cmt = null;
    this.desc = null;
    this.src = null;
    this.link = [];
    this.number = 0;
    this.type = null;
    this.extensions = null;
    this.trkseg = [];
}

function trkseg() {
    this.trkpt = [];
    this.extensions = null;
}

function gpx()
{
    this.metadata = [];
    this.wpt = [];
    this.rte = [];
    this.trk = [];
    this.extensions = [];
}

// helper functions

function loadGpx(gpx_xml_doc) {
    gpx_obj = new gpx();
    gpx_obj.trk = loadTracks(gpx_xml_doc);
    gpx_obj.wpt = loadWaypoints(gpx_xml_doc);
    return gpx_obj;
}

function loadWaypoints(gpx_xml_doc) {
    var waypoints = [];
    $(gpx_xml_doc).find("wpt").each(function(){
            var lat = $(this).attr('lat');
            var lon = $(this).attr('lon');
            var time = $(this).find('time').text();
            var waypoint = new wpt(lat, lon);
            waypoint.name = "(" + lat + ", " + lon + ")";
            waypoint.time = time;
            if (waypoint.time != null) {
                var date = new Date(waypoint.time);
            }
            waypoints.push(waypoint);
        });
    waypoints.sort(function(a, b){
            if (a.time > b.time) {
                return 1;
            }
            return -1;
        });
    return waypoints;
}

function loadTracks(gpx_xml_doc) {
    var tracks = [];
    $(gpx_xml_doc).find("trk").each(function(){
            var track = loadTrack(this);
            tracks.push(track);
        });
    return tracks;
}

function loadTrack(track) {
    var trk_obj = new trk();
    $(track).find("trkseg").each(function(){
            var trkseg_obj = new trkseg();
            $(this).find("trkpt").each(function(){
                    var lat = $(this).attr('lat');
                    var lon = $(this).attr('lon');
                    var time = $(this).find('time').text();
                    var trkpt_obj = new wpt(lat,lon);
                    trkpt_obj.time = time;
                    trkpt_obj.timestamp = 0;
                    if (trkpt_obj.time != null) {
                        var date = new Date(trkpt_obj.time);
                    }
                    trkpt_obj.name = "(" + lat + ", " + lon + ")";
                    trkseg_obj.trkpt.push(trkpt_obj);
                });
            trkseg_obj.trkpt.sort(function(a, b){
                    if (a.time > b.time) {
                        return 1;
                    }
                    return -1;
                });
            trk_obj.trkseg.push(trkseg_obj);
        });
    return trk_obj;
}

window.Collection = (function(){
        // http://www.bennadel.com/blog/2292-extending-javascript-arrays-while-keeping-native-bracket-notation-functionality.htm
        function Collection(){
            var collection = Object.create( Array.prototype );
            collection = (Array.apply( collection, arguments ) || collection);
            Collection.injectClassMethods( collection );
            return( collection );
        }
        Collection.injectClassMethods = function( collection ){
            for (var method in Collection.prototype){
                if (Collection.prototype.hasOwnProperty( method )){
                    collection[ method ] = Collection.prototype[ method ];
                }
            }
            return( collection );
        };
        Collection.fromArray = function( array ){
            var collection = Collection.apply( null, array );
            return( collection );
        };
        Collection.isArray = function( value ){
            var stringValue = Object.prototype.toString.call( value );
            return( stringValue.toLowerCase() === "[object array]" );
        };
        Collection.prototype = {
            add: function( value ){
                if (Collection.isArray( value )){
                    for (var i = 0 ; i < value.length ; i++){
                        Array.prototype.push.call( this, value[ i ] );
                    }
                } else {
                   Array.prototype.push.call( this, value );

                }
                return( this );

            },
            addAll: function(){
                for (var i = 0 ; i < arguments.length ; i++){
                    this.add( arguments[ i ] );
                }
                return( this );
            }

        };
        return( Collection );
    }).call( {} );
