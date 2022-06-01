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

import logging, time
import json
import boto3 # AWS library
from .client import Client
import os

MAX_PAYLOAD_BYTES = 1024*1024   # Kinesis max payload size is 1MB
# Kinesis input limitations: 1 MB/s or 1000 messages/sec, per shard

class Kinesis(Client):
    def __init__(self, instance_name, context, params):
        logging.info("Initialising Kinesis client")
        self.instance_name = instance_name
        self.context = context
        self.params = params
        if "setenv" in params:
            for (key, value) in params["setenv"].items():
                logging.info("SETENV "+key+" "+value)
                os.environ[key] = value

    def add_device(self, device_id, time, properties):
        pass
    
    def update_device(self, device_id, time, properties):
        pass

    def get_device(self, device_id):
        pass
    
    def get_devices(self):
        pass
    
    def delete_device(self, device_id):
        pass

    def enter_interactive(self):
        pass

    def tick(self):
        pass

    def async_command(self, argv):
        pass

    def close(self):
        pass


session = boto3.Session(profile_name="playground")
kinesis = session.client("kinesis")
data = [{ "$ts" : 123, "$id" : "1", "a" : 1 }]
kinesis.put_record(StreamName="Flight-Simulator", Data=json.dumps(data), PartitionKey = "1")
