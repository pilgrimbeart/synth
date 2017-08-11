# abc for a client.
from abc import ABCMeta, abstractmethod

class Client:
    __metaclass__ = ABCMeta

    @abstractmethod
    def add_device(self, device_id, time, properties):  # Add a device (if exists then overwrite)
        pass                                            # and update its properties

    @abstractmethod
    def update_device(self, device_id, time, properties):
        pass

    @abstractmethod
    def get_device(self):                               # Get parameters for one device
        return None

    @abstractmethod
    def get_devices(self):                              # Get list of device_ids for all devices
        return None

    @abstractmethod
    def delete_device(self, device_id):                 # Delete existing device
        pass

    @abstractmethod
    def enter_interactive(self):                        # Some clients need to be told when
        pass                                            # we move from historical to live mode

    @abstractmethod
    def tick(self):                                     # Called periodically for housekeeping
        pass

    @abstractmethod
    def flush(self):                                    # Write all pending data (e.g. before exiting)
        pass
