#!/usr/bin/env python
r"""
Kinesis client
==================
This client posts event data into an Amazon Kinesis queue.

Kinesis client specification
--------------------------------
The client accepts the following parameters (usually found in the "On*.json" file in ../synth_accounts)::

    "client" : {
        "type" : "kinesis",
    }

To make this work, you must run "aws configure" on your command line and create a profile in ~/.aws/config
To create the credentials go to https://console.aws.amazon.com/iam/home and select Users, then yourself.

Because the post rate into AWS seems (as of 2022) to be limited to around 14 posts/sec, we use the multiprocessing module to give us more "oomph".
"""
#
# Copyright (c) 2022 DevicePilot Ltd.
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

# 
import logging
import os
from .client import Client
from .client_helpers import client_workers

MAX_MESSAGES_PER_POST = 500     # Kinesis requirement
REPORT_EVERY_S = 60
BACKOFF_S = 0  # How long to wait when AWS says its under-provisioned (set to 0 to force AWS to just cope!)

DEFAULT_NUM_WORKERS = 1
POLL_PERIOD_S = 0.1 # How often the workers poll for new work

class Kinesis(Client):
    def __init__(self, instance_name, context, params, logfile_abspath):
        logging.info("Initialising Kinesis client with " + str(params))
        self.instance_name = instance_name
        self.context = context
        self.params = params
        if "setenv" in params:
            for (key, value) in params["setenv"].items():
                # logging.info("SETENV "+key+" "+value)
                os.environ[key] = value

        self.num_workers = params.get("num_workers", DEFAULT_NUM_WORKERS)
        logging.info("Kinesis module using "+str(self.num_workers)+" worker sub-processes to provide write bandwidth")

        explode_factor = params.get("explode_factor", 1)
        if explode_factor != 1:
            logging.info("Kinesis explode factor set to "+str(explode_factor))

        self.workers = []
        for w in range(self.num_workers):
            self.workers.append(client_workers.WorkerParent(params, logfile_abspath))

    def add_device(self, device_id, time, properties):
        pass
    
    def update_device(self, device_id, time, properties):
        w = hash(properties["$id"]) % self.num_workers   # Shard onto workers by ID (so data from each device stays in sequence). Python hash is stable per run, not across runs.
        self.workers[w].enqueue(properties)

    def get_device(self, device_id):
        pass
    
    def get_devices(self):
        pass
    
    def delete_device(self, device_id):
        pass

    def enter_interactive(self):
        pass

    def tick(self, t):
        for w in self.workers:
            w.tick(t)

        client_workers.output_stats(self.workers)

    def async_command(self, argv):
        pass

    def close(self):
        for w in self.workers:
            w.wait_until_stopped()

    # ----
    def flush_queue():
       pass 


