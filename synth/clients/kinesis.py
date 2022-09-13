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

Because the post rate into AWS seems (as of 2022) to be limited to around 14 posts/sec, we use the multiprocessing module to give us more oomph
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
from .client import Client
from common import ISO8601
from multiprocessing import Process as MP_Process
from multiprocessing import Queue as MP_Queue
import queue    # Multiprocessing uses this internally, and returns queue.Empty exception

import boto3 # AWS library

MAX_PAYLOAD_BYTES = 1024*1024   # Kinesis max payload size is 1MB. Kinesis input limitations: 1 MB/s or 1000 messages/sec, per shard
MAX_MESSAGES_PER_POST = 500     # Kinesis requirement
REPORT_EVERY_S = 60
BACKOFF_S = 0  # How long to wait when AWS says its under-provisioned (set to 0 to force AWS to just cope!)
MAX_EXPLODE = 1_000_000

NUM_WORKERS = 4
POLL_PERIOD_S = 0.1 # How often the workers poll for new work

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

        explode_factor = params.get("explode_factor", 1)
        if explode_factor != 1:
            logging.info("Kinesis explode factor set to "+str(explode_factor))

        profile_name = params.get("profile_name", None)
        stream_name = params["stream_name"]
        logging.info("Sending to Kinesis profile_name " + str(profile_name) + ", stream_name " + str(stream_name))

        logging.info("Kinesis module using "+str(NUM_WORKERS)+" worker sub-processes to provide enough write bandwidth")
        self.workers = []
        for w in range(NUM_WORKERS):
            self.workers.append(WorkerParent(profile_name, stream_name, explode_factor))
        self.next_worker_to_use = 0

    def add_device(self, device_id, time, properties):
        # logging.info("Kinesis: Add device " + str(properties))
        pass
    
    def update_device(self, device_id, time, properties):
        self.workers[self.next_worker_to_use].send(properties)
        self.next_worker_to_use = (self.next_worker_to_use + 1) % NUM_WORKERS

    def get_device(self, device_id):
        pass
    
    def get_devices(self):
        pass
    
    def delete_device(self, device_id):
        pass

    def enter_interactive(self):
        pass

    def count_shards(self, result):
        max_shard_seen = 0
        ids = []
        for r in result["Records"]:
            if "ShardId" in r:  # Only successful records have a shard id
                id = int(r["ShardId"][-12:])    # Last 12 digits is shard id
                if id not in ids:
                    ids.append(id)
                max_shard_seen = max(max_shard_seen, id)
        shards = max_shard_seen + 1
        self.max_shards_seen = max(self.max_shards_seen, shards)
        self.max_shards_seen_recently = max(self.max_shards_seen_recently, shards)
        # logging.info(str(max_shard_seen+1) + " shards " + str(ids))


    def tick(self):
        return

    def async_command(self, argv):
        pass

    def close(self):
        pass

    # ----
    def flush_queue():
       pass 


## Multiprocessing

class WorkerParent():   # Create a worker, and communicate with it
    def __init__(self, profile_name, stream_name, explode_factor):
        self.q = MP_Queue()
        self.p = MP_Process(target=child_func, args=(self.q,), name="synth_worker")
        self.p.start()
        self.q.put((profile_name, stream_name, explode_factor)) # First item on queue is parameters, matching *** below

    def send(self, data):
        self.q.put(data)

if __name__ == '__main__':
    w1 = SynthWorker()
    w2 = SynthWorker()
    w1.send("Hello")
    w2.send("There")
    time.sleep(3)
    w1.send("Wonder")
    w2.send("Bubs")
    time.sleep(3)
    w1.send(None)
    w2.send(None)


def child_func(q):  # Executed in the target processes
    (profile_name, stream_name, explode_factor) = q.get()    # First item sent is our parameters, matching *** above
    worker = Worker(profile_name, stream_name, explode_factor)
    while True:
        try:
            v = q.get(timeout=POLL_PERIOD_S)
            logging.info("Worker "+str(os.getpid())+" got from queue "+str(v)+". Queue size now "+str(q.qsize()))
            if v is None:
                logging.warning("Worker ",os.getpid(),"exiting")
                return
            worker.enqueue(v)
        except queue.Empty:
            pass

        worker.tick()


class Worker(): # The worker itself, which runs IN A SEPARATE PROCESS
    def __init__(self, profile_name, stream_name, explode_factor):
        logging.info("Kinesis worker "+str(os.getpid())+" initialising for profile "+str(profile_name)+" and stream "+str(stream_name))
        self.profile_name = profile_name
        self.stream_name = stream_name
        self.explode_factor = explode_factor

        if self.profile_name is None:
            session = boto3.Session()
        else:
            session = boto3.Session(self.profile_name)
        if session.get_credentials().secret_key is None:
            logging.error("AWS secret key is None, so this isn't going to work")
        self.kinesis_client = session.client("kinesis")

        self.queue = []

        self.start_time = time.time()
        self.last_report_time = 0
        self.num_blocks_sent_ever = 0
        self.num_blocks_sent_recently = 0
        self.max_shards_seen = 0
        self.max_shards_seen_recently = 0


    def enqueue(self, properties):
        if self.explode_factor == 1:
            self.queue.append({
                    'Data' : json.dumps(properties),                    # This is format in which Kinesis expects every item
                    'PartitionKey' : str(properties['$id'])
                })
        else:
            LEN = len(str(MAX_EXPLODE))
            LENFORMAT = "%0" + str(LEN) + "d"
            LOCATOR = "X" * LEN
            base_id = properties["$id"]
            new_props = properties.copy()
            new_props["$id"] = new_props["$id"] + "_" + LOCATOR
            data_str = json.dumps(new_props)        # json.dumps() is SLOW, so only use it once
            start = data_str.find(LOCATOR)
            end = start + len(LOCATOR)
            pre_str = data_str[:start]
            post_str = data_str[end:]
            id_str = properties["$id"] + "_"

            for e in range(self.explode_factor):
                e_str = LENFORMAT % e   # 00001 or whatever
                d = {
                        'Data' : pre_str + e_str + post_str,
                        'PartitionKey' : id_str + e_str
                    }
                self.queue.append(d)

    def tick(self):
        while len(self.queue) > 0:  # Will result in last send being a partial block - not best efficiency, but alternative is to leave a partial block unsent (perhaps forever)
            num = min(MAX_MESSAGES_PER_POST, len(self.queue))
            self.send_to_kinesis(self.queue[0:num])
            self.num_blocks_sent_ever += 1
            self.num_blocks_sent_recently += 1
            self.queue = self.queue[num:]

        t =  time.time()
        if t > self.last_report_time + REPORT_EVERY_S :
            elap = t - self.start_time
            logging.info("Kinesis worker " + str(os.getpid()) + ": {:,} blocks sent ever in {:0.1f}s which is {:0.1f} blocks/s with max shards {:}. Over last {:}s, rate was {:0.1f} blocks/s and max shards {:}".format(
                self.num_blocks_sent_ever,
                elap,
                self.num_blocks_sent_ever / elap,
                self.max_shards_seen,
                REPORT_EVERY_S,
                self.num_blocks_sent_recently / float(REPORT_EVERY_S),
                self.max_shards_seen_recently))
            self.num_blocks_sent_recently = 0
            self.max_shards_seen_recently = 0
            self.last_report_time = t

    def send_to_kinesis(self, records, retries=0):
        # logging.info("Worker sending "+str(len(records))+" records to Kinesis and queue length now "+str(len(self.queue)))
        if retries==0:
            s = "Sending"
        else:
            s = "Re-sending"
        # logging.info(s + " " + str(len(records)) + " messages")
        result = self.kinesis_client.put_records(Records=records, StreamName=self.stream_name)
        # self.count_shards(result)
        fails = result["FailedRecordCount"]
        if fails != 0:
            # Result["Records"] is all of the records. The failed ones (only) have an ErrorCode field.
            errors = result["Records"]
            new_records = []
            errors_seen = []
            for i in range(len(records)):
                if "ErrorCode" in errors[i]:
                    new_records.append(records[i])
                    ec = errors[i]["ErrorCode"]
                    if ec not in errors_seen:
                        errors_seen.append(ec)
            logging.error("Kinesis: Failed to post " + str(fails) + " of " + str(len(records)) + " records (retries so far " + str(retries)+") " + str(errors_seen))
            time.sleep(BACKOFF_S)
            self.send_to_kinesis(new_records, retries+1)
            # "Records": [ 
            #    { 
            #        "ErrorCode": "string",
            #        "ErrorMessage": "string",
            #        "SequenceNumber": "string",
            #        "ShardId": "string"
            #    }
    
