r"""
Filesystem Client
=================
This client posts event data to the local filesystem, and is useful for offline testing of scenarios.
In addition to the .evt file that Synth emits, the Filesystem client also emits
a .csv file.

Filesystem Client specification
-------------------------------
The client accepts the following parameters
(usually found in the "On*.json" file in ../synth_accounts)::

    "client" :
    {
        "type" : "filesystem",
        "filename" :"OnFStest"
    }

There are no Filesystem-specific event actions.
"""
#
# Copyright (c) 2017 DevicePilot Ltd.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import json
from clients.client import Client
from common import evt2csv
from common import json_writer

SEP = "!"

class Filesystem(Client):
    """Filesystem client for Synth.

        We don't know a-priori which properties we'll encounter, but ultimately we need
        to write a CSV file which includes a column header for each property.
        So we use evt2csv to accumulate and write at the end.
    """
    def __init__(self, instance_name, params):
        self.params = params
        self.events = {} # A dict of events in a format handled by evt2csv
        self.json_stream = json_writer.Stream(instance_name)

    def add_device(self, device_id, time, properties):
        self.update_device(device_id, time, properties)

    def update_device(self, device_id, time, properties):
        properties["$id"] = device_id # Ensure we always specify these
        properties["$ts"] = time
        evt2csv.insert_properties(self.events, properties)
        self.json_stream.write_event(properties)
        return True

    def get_device(self):
        return None

    def get_devices(self):
        return None

    def delete_device(self):
        pass
    
    def enter_interactive(self):
        pass

    def bulk_upload(self, file_list):
        logging.warning("Bulk upload action ignored by filesystem client")
        pass

    def tick(self):
        pass
    
    def close(self):
        """Called to clean up on exiting."""
        self.json_stream.close()
        logging.info("Preparing CSV file")
        csv = evt2csv.convert_to_csv(self.events)
        logging.info("Writing CSV file")
        filename = "../synth_logs/"+self.params["filename"]+".csv"
        open(filename,"wt").write(csv)
        logging.info("A total of "+str(csv.count("\n"))+" rows (including a header row) were written to "+filename)        
        return
