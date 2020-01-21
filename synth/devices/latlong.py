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

        "devices_per_address" : [2,5]           If specified, re-uses each address this many times. If this value is a 2-item list, it's used as the range of a random number.
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
import random
import logging

class Latlong(Device):
    address_index = 0
    prev_address_props = None
    further_devices_at_this_address = 0

    def __init__(self, instance_name, time, engine, update_callback, context, params):
        def get_new_address():
            if "addresses" in params["latlong"]:    # Iterate through a provided list of addresses
                num_addr = len(params["latlong"]["addresses"])
                addr = params["latlong"]["addresses"][Latlong.address_index % num_addr]
                Latlong.address_index += 1
                if Latlong.address_index > num_addr:
                    logging.warning("Not enough addresses specified in latlong{} for device "+self.get_property("$id")+" so re-using addresses")
                gmk = context.get("google_maps_key", None)
                (lon,lat) = google_maps.address_to_lon_lat(addr, gmk)               # address -> (lon,lat)
                props = { "latitude" : lat, "longitude" : lon, "address" : addr }
                address_info = google_maps.lon_lat_to_address(lon,lat, gmk)         # (lon,lat) -> address   (to get detailed address fields)
                for name,value in address_info.items():
                    props[name] = value
            else:   # Use geo module to pick locations randomly within an area
                picker = geo.geo_pick(context, params["latlong"])
                (lon, lat) = picker.pick()
                props = { "latitude" : lat, "longitude" : lon }
                for name, value in picker.addresses():
                    props[name] = value
            return props

        super(Latlong,self).__init__(instance_name, time, engine, update_callback, context, params)

        dpa = params["latlong"].get("devices_per_address", 1)
        if dpa == 1:
            address_props = get_new_address()
        else:
            if Latlong.further_devices_at_this_address > 0: # Still some devices to put at this address
                address_props = Latlong.prev_address_props
            else:
                Latlong.further_devices_at_this_address = random.randrange(dpa[0], dpa[1])
                address_props = get_new_address()
            Latlong.further_devices_at_this_address -= 1
                

        self.set_properties(address_props)
        Latlong.prev_address_props = address_props


    def comms_ok(self):
        return super(Latlong,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Latlong,self).external_event(event_name, arg)

    def close(self):
        super(Latlong,self).close()

