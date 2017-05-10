def num_devices():
    global devices
    n = len(devices)
    return n

def external_event(params):
    # Accept events from outside world
    # (these have already been synchronised via the event queue so we don't need to worry about thread-safety here)
    global devices
    body = params["body"]
    try:
        logging.info("external Event received: " + str(params))
        for d in devices:
            if d.properties["$id"] == body["deviceId"]:
                arg = None
                if "arg" in body:
                    arg = body["arg"]
                d.external_event(body["eventName"], arg)
                return
        e = "No such devices"  # + str(deviceID) + " for incoming event " + str(eventName)
        log_string(e)
    except Exception as e:
        log_string("Error processing external event")
        logging.error("Error processing externalEvent: " + str(e))
        logging.error(traceback.format_exc())


class Device:
    def __init__(self, props):
        self.properties = props
        devices.append(self)

        self.do_comms(self.properties)

    def external_event(self, event_name, arg):
        s = "Processing external event " + event_name + " for devices " + str(self.properties["$id"])
        log_string(s)
        if event_name == "replaceBattery":
            self.set_property("battery", 100)
            self.start_ticks()

        # All other commands require devices to be functional!
        if self.get_property("battery") <= 0:
            log_string("...ignored because battery flat")
            return
        if not self.commsOK:
            log_string("...ignored because comms down")
            return

        if event_name == "upgradeFirmware":
            self.set_property("firmware", arg)
        if event_name == "factoryReset":
            self.set_property("firmware", self.get_property("factoryFirmware"))



    

# Model for comms unreliability
# -----------------------------
# Two variables define comms (un)reliability:
# a) up/down period: (secs) The typical period over which comms might change between working and failed state.
#    We use an exponential distribution with this value as the mean.
# b) reliability: (0..1) The chance of comms working at any moment in time
# The comms state is then driven independently of other actions.
# 
# Chance of comms failing at any moment is [0..1]
# Python function random.expovariate(lambda) returns values from 0 to infinity, with most common values in a hump in
# the middle such that that mean value is 1.0/<lambda>
