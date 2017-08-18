from device import Device
from geo import geo

pp = geo.pointPicker()  # Very expensive, so do only once

##    if "area_centre" in params:
##        pp.setArea([params["area_centre"], params["area_radius"]])

class Geo(Device):
    def __init__(self, time, engine, updateCallback, params):
        super(Geo,self).__init__(time, engine, updateCallback, params)
        self.area_centre = params["geo"].get("area_centre", None)
        self.area_radius = params["geo"].get("area_radius", None)
        # SET pp AREA HERE (but without thrashing GMaps!)
        (lon,lat) = pp.pickPoint()
        self.setProperties( { 'latitude' : lat, 'longitude' : lon } )

    def externalEvent(self, eventName, arg):
        super(Geo,self).externalEvent(eventName, arg)
        pass
