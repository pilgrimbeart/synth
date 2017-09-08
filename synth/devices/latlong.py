from device import Device
from geo import geo

pp = geo.point_picker()  # Very expensive, so do only once

class Latlong(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        super(Latlong,self).__init__(instance_name, time, engine, update_callback, params)
        self.area_centre = params["latlong"].get("area_centre", None)
        self.area_radius = params["latlong"].get("area_radius", None)
        area = None
        if self.area_centre != None:
            area = [self.area_centre, self.area_radius]
        (lon,lat) = pp.pick_point(area)
        self.set_properties( { 'latitude' : lat, 'longitude' : lon } )

    def comms_ok(self):
        return super(Latlong,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Latlong,self).external_event(event_name, arg)

    def finish(self):
        super(Latlong,self).finish()

