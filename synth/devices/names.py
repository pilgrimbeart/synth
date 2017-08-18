from device import Device
import peopleNames

class Names(Device):
    def __init__(self, time, engine, updateCallback, params):
        super(Names,self).__init__(time, engine, updateCallback, params)
        print "Names __init__"
        self.setProperties(
            { 'first_name' : peopleNames.firstName(self.properties["$id"]),
              'last_name' :  peopleNames.lastName(self.properties["$id"]) } )

    def externalEvent(self, eventName, arg):
        super(Names,self).externalEvent(eventName, arg)
        pass
