#!/usr/bin/env python
r"""
Client_Workers
==================
A library on top of Python's multiprocessing module, for creating and managing multiple worker processes, to achieve more POST bandwidth into AWS

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
import logging, time
import json
import os, sys
from common import merge_test
from multiprocessing import Process as MP_Process
from multiprocessing import Queue as MP_Queue
import queue    # Multiprocessing uses this internally, and returns queue.Empty exception
import boto3, botocore
from botocore.config import Config

from . import kinesis_worker, timestream_worker

KINESIS_MAX_MESSAGES_PER_POST = 500     # Kinesis requirement
REPORT_EVERY_S = 60
BACKOFF_S = 0  # How long to wait when AWS says its under-provisioned (set to 0 to force AWS to just cope!)
MAX_EXPLODE = 1_000_000

POLL_PERIOD_S = 0.1 # How often the workers poll for new work

class WorkerParent():   # Create a worker, and communicate with it
    def __init__(self, params):
        self.merge_buffer = {}  # Messages, keyed by ID
        self.time_at_last_tick = 0

        self.q = MP_Queue()
        assert "type" in params, "Client params must specify a type=kinesis/timestream"
        if params["type"] == "kinesis":
            child_func = kinesis_worker.child_func
        elif params["type"] == "timestream":
            child_func = timestream_worker.child_func
        else:
            assert False, "Invalid option for type param in client params"
        self.p = MP_Process(target=child_func, args=(self.q,), name="synth_worker")
        self.p.start()
        self.q.put(params) # First item on queue is parameters

    def enqueue(self, properties):
        device_id = properties["$id"]
        if device_id in self.merge_buffer:
            if merge_test.ok(self.merge_buffer[device_id], properties):
                self.merge_buffer[device_id].update(properties)
        else:   
            self.merge_buffer[device_id] = properties

    def tick(self, t):
        if t != self.time_at_last_tick:
            for (device, properties) in self.merge_buffer.items():
                self._send(properties)
            self.merge_buffer = {}
            self.time_at_last_tick = t

    def _send(self, data):  # Don't use this directly if you want message merging
        self.q.put(data)
        if not self.p.is_alive():
            logging.error("Worker " + str(self.p.pid) + " has died - so terminating")
            assert(False)

    def wait_until_stopped(self):
        logging.info("Telling worker " + str(self.p.pid) + " to stop")
        self._send(None)    # Signal to stop
        logging.info("Waiting for worker " + str(self.p.pid) + " to stop")
        self.p.join()
        logging.info("Worker " + str(self.p.pid) + " has stopped")

