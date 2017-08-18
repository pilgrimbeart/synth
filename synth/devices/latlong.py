from device import Device
from geo import geo

pp = geo.pointPicker()  # Very expensive, so do only once

class Latlong(Device):
    def __init__(self, time, engine, updateCallback, params):
        super(Latlong,self).__init__(time, engine, updateCallback, params)
        self.area_centre = params["latlong"].get("area_centre", None)
        self.area_radius = params["latlong"].get("area_radius", None)
        area = None
        if self.area_centre != None:
            area = [self.area_centre, self.area_radius]
        (lon,lat) = pp.pickPoint(area)
        self.setProperties( { 'latitude' : lat, 'longitude' : lon } )

    def externalEvent(self, eventName, arg):
        super(Latlong,self).externalEvent(eventName, arg)
        pass
