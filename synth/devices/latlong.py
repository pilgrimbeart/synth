"""
latlong
=======
Scatters devices on the surface of the Earth in a realistic way according to population.
If no arguments are provided, devices are scattered across the whole Earth.
Uses a Google Maps API.

Configurable parameters::

    {
        "generate_addresses" : true/false       If true then creates address_* properties (street, town, country etc.)

        "area_centre" : e.g. "London, UK"       } optional, but both must be specified if either are
        "area_radius" : e.g. "Manchester, UK"   } 
        -or-
        "addresses" : e.g. ["London, UK", "Manchester, UK"] } a set of locations which are picked device-by-device

        "map_file" : e.g. "devicepilot_logo" - optional
        "google_maps_key" : "xyz" } Google Maps now requires this. Often defined in ../synth_accounts/default.json
    }

Device properties created::

    {
        "latitude" : latitude in degrees as a floating-point number
        "longitude" : longitude in degrees as a floating-point number
    }
"""

from .device import Device
from common.geo import geo, google_maps
import logging

class Latlong(Device):
    address_index = 0
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Latlong,self).__init__(instance_name, time, engine, update_callback, context, params)

        if "addresses" in params["latlong"]:    # Defined set of addresses
            num_addr = len(params["latlong"]["addresses"])
            addr = params["latlong"]["addresses"][Latlong.address_index % num_addr]
            Latlong.address_index += 1
            if Latlong.address_index > num_addr:
                logging.warning("Not enough addresses specified in latlong{} for device "+self.get_property("$id")+" so re-using addresses")
            (lon,lat) = google_maps.address_to_lon_lat(addr, context.get("google_maps_key", None))
            self.set_properties( { 'latitude' : lat, 'longitude' : lon } )
            self.set_property("address", addr)
        else:   # Use geo module to pick locations randomly within an area
            picker = geo.geo_pick(context, params["latlong"])
            (lon, lat) = picker.pick()
            self.set_properties( { 'latitude' : lat, 'longitude' : lon } )
            for name, value in picker.addresses():
                self.set_property(name, value)

    def comms_ok(self):
        return super(Latlong,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Latlong,self).external_event(event_name, arg)

    def close(self):
        super(Latlong,self).close()

