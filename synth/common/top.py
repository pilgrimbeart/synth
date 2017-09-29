
class top():
    def __init__(self):
        self.top_devices = {}

    def update(self, new_properties):
        """ 'top' means the latest-known value of each property, for each device.
            The structure of top is:
                A set of devices
                    Each of which is a set of properties
                        Each of which is a (time, value) tuple """
        new_id = new_properties["$id"]
        new_ts = new_properties["$ts"]
        if not new_id in self.top_devices:
            self.top_devices[new_id] = {}
        existing_props = self.top_devices[new_id]
        for new_prop, new_value in new_properties.iteritems():
            if new_prop not in existing_props:
                existing_props[new_prop] = (new_ts, new_value)
            else:
                existing_ts = existing_props[new_prop][0]
                if new_ts >= existing_ts:   # Only update if timestamp is newer
                    existing_props[new_prop] = (new_ts, new_value)

##        print "top.update():"
##        print "new_properties:"
##        print json.dumps(new_properties, indent=4, sort_keys=True)
##        print "so top now:"
##        print json.dumps(self.top_devices, indent=4, sort_keys=True)        

    def get(self):
        """Return a list of latest property-values by device""" 
        L = []            
        for dev, proptuples in self.top_devices.iteritems():
            props = {}
            for name,time_and_value in proptuples.iteritems():  # Assemble normal properties set (without times)
                props[name] = time_and_value[1]
            L.append(props)
        return L
