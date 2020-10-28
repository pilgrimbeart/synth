# abc for a client.
from abc import ABCMeta, abstractmethod

class Client:
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, instance_name, context, params):
        pass

    @abstractmethod
    def add_device(self, device_id, time, properties):
        """Add a device (if exists then overwrite) and update its properties."""
        pass

    @abstractmethod
    def update_device(self, device_id, time, properties):
        """Update an existing device's properties (for some clients it's an error to update a device before calling add_device()"""
        pass

    @abstractmethod
    def get_device(self):
        """Get parameters for one device."""
        return None

    @abstractmethod
    def get_devices(self):
        """Get list of device_ids for all devices."""
        return None

    @abstractmethod
    def delete_device(self, device_id):
        """Delete existing device."""
        pass

    @abstractmethod
    def enter_interactive(self):
        """Some clients need to be told when we move from historical to live mode."""
        pass

    @abstractmethod
    def bulk_upload(self, file_list):
        """Upload bulk data"""
        pass

    @abstractmethod
    def tick(self):
        """Called periodically for housekeeping."""
        pass

    @abstractmethod
    def async_command(self, argv):
        """Asynchronous commands into this client"""
        pass

    @abstractmethod
    def close(self):
        """Write all pending data (e.g. before exiting)."""
        pass
