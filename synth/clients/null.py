r"""
null client
=================
This client throws everything away! - useful for testing performance impacts of other clients.
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
from .client import Client
from common import evt2csv
from common import json_writer

class Null(Client):
    """Null client for Synth"""
    def __init__(self, instance_name, context, params):
        self.params = params

    def add_device(self, device_id, time, properties):
        pass

    def update_device(self, device_id, time, properties):
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
        pass

    def tick(self):
        pass
    
    def close(self):
        logging.info("All your data was thrown away")
        return
