"""
button
======
Presses a button on the device, according to some timefunction.

Configurable parameters::

    {
        "timefunction" : A time function specification.
    }

Device properties created::

    {
        "button_press" : Sent as a 1 on every button press
    }
    
"""
   
import logging
from device import Device
from common import importer

class Button(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        """A button which gets pressed according to some time function"""
        super(Button, self).__init__(instance_name, time, engine, update_callback, params)
        tf = params["button"]["timefunction"]
        self.button_timefunction = importer.get_class("timefunction", tf.keys()[0])(engine, tf[tf.keys()[0]])
        engine.register_event_at(self.button_timefunction.next_change(), self.tick_button, self)

    def comms_ok(self):
        return super(Button, self).comms_ok()

    def external_event(self, event_name, arg):
        super(Button, self).external_event(event_name, arg)

    def close(self, err_str):
        super(Button, self).close(err_str)

    # Private methods

    def tick_button(self, _):
        if self.button_timefunction.state() > 0:   # Only press when timefunction is not zero (i.e. not on return edge of waveforms)
            if self.properties.get("battery",100) > 0:    # If there's no battery, or there is an it's not flat
                self.set_property("button_press", 1)
        self.engine.register_event_at(self.button_timefunction.next_change(), self.tick_button, self)
