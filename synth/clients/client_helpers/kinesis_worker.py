#!/usr/bin/env python
r"""
Kinesis_Worker
==================
Runs in separate process to send data to Kinesis

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
import os
import queue    # Multiprocessing uses this internally, and returns queue.Empty exception
import multiprocessing
import setproctitle

import boto3 # AWS library

KINESIS_MAX_MESSAGES_PER_POST = 500     # Kinesis requirement
REPORT_EVERY_S = 60
BACKOFF_S = 0  # How long to wait when AWS says its under-provisioned (set to 0 to force AWS to just cope!)
MAX_EXPLODE = 1_000_000

POLL_PERIOD_S = 0.1 # How often the workers poll for new work

### This code is executed in the target process(es), so must not refer to Synth environment

def child_func(qtx, qrx):   # qtx is messages to send, qrx is feedback to Synth
    setproctitle.setproctitle(multiprocessing.current_process().name)
    (params, logfile_abspath) = qtx.get()    # First item sent is a dict of params
    worker = Worker(params)
    while True:
        try:
            v = qtx.get(timeout=POLL_PERIOD_S)
            # logging.info("Worker "+str(os.getpid())+" got from queue "+str(v)+". Queue size now "+str(q.qsize()))
            if v is None:
                logging.info("Worker "+str(os.getpid()) + " requested to exit")
                return
            worker.enqueue(v)
            worker.note_input_queuesize(qtx.qsize())
        except queue.Empty:
            pass

        result = worker.tick()
        if result:
            qrx.put(result)


class Worker():
    def __init__(self, params):
        logging.info("Kinesis Worker "+str(os.getpid())+" initialising with params "+str(params))
        self.params = params

        if "profile_name" in self.params:
            session = boto3.Session(self.params["profile_name"])
        else:
            session = boto3.Session()

        if session.get_credentials().secret_key:
            logging.info("Kinesis worker sees AWS secret key is set")
        else:
            logging.error("Kinesis worker sees no AWS secret key, so this isn't going to work")
        self.kinesis_client = session.client("kinesis")

        self.queue = []

        self.start_time = time.time()
        self.last_report_time = 0
        self.num_blocks_sent_ever = 0
        self.num_blocks_sent_recently = 0
        self.max_shards_seen = 0
        self.max_shards_seen_recently = 0
        self.max_queue_size_recently = 0
        self.slowest_post_recently = 0
        self.post_stats = [0,0,0,0,0]
        self.total_post_latency = 0


    def note_input_queuesize(self, n):
        self.max_queue_size_recently = max(self.max_queue_size_recently, n)

    def enqueue(self, properties):
        if ("explode_factor" not in self.params) or (self.params["explode_factor"] == 1) or ("dont_explode" in properties):
            properties.pop("dont_explode", None)
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

            for e in range(self.params["explode_factor"]):
                e_str = LENFORMAT % e   # 00001 or whatever
                d = {
                        'Data' : pre_str + e_str + post_str,
                        'PartitionKey' : id_str + e_str
                    }
                self.queue.append(d)

    def tick(self):
        # Occasionally return stats
        result = None
        t =  time.time()
        if t > self.last_report_time + REPORT_EVERY_S :
            elap = t - self.start_time
            tDelta = 0
            if len(self.queue) > 0:
                props = json.loads(self.queue[0]["Data"])
                tDelta = int(time.time() - props["$ts"])

            result = {
                "num_blocks_sent_ever" : self.num_blocks_sent_ever,
                "max_queue_size_recently" : self.max_queue_size_recently,
                "slowest_post_recently" : self.slowest_post_recently,
                "post_stats" : self.post_stats,
                "total_post_latency" : self.total_post_latency,
                "t_delta" : tDelta
            }

            self.num_blocks_sent_recently = 0
            self.slowest_post_recently = 0
            self.max_shards_seen_recently = 0
            self.max_queue_size_recently = 0
            self.last_report_time = t

        # Transmit waiting messages
        while len(self.queue) > 0:  # Will result in last send being a partial block - not best efficiency, but alternative is to leave a partial block unsent (perhaps forever)
            tA = time.time()
            num = min(KINESIS_MAX_MESSAGES_PER_POST, len(self.queue))
            self.send_to_kinesis(self.queue[0:num])
            self.num_blocks_sent_ever += 1
            self.num_blocks_sent_recently += 1
            self.queue = self.queue[num:]
            tB = time.time()
            
            tTot = tB-tA
            if tTot < 0.1:
                self.post_stats[0] += 1
            elif tTot < 0.2:
                self.post_stats[1] += 1
            elif tTot < 0.5:
                self.post_stats[2] += 1
            elif tTot < 1.0:
                self.post_stats[3] += 1
            else:
                self.post_stats[4] += 1
            if tTot > self.slowest_post_recently:
                self.slowest_post_recently = tTot
            self.total_post_latency += tTot

        return result

    def send_to_kinesis(self, records, retries=0):
        if retries==0:
            s = "Sending"
        else:
            s = "Re-sending"
        result = self.kinesis_client.put_records(Records=records, StreamName=self.params["stream_name"])
        self.count_shards(result)
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
            logging.warning("Kinesis: Failed to post " + str(fails) + " of " + str(len(records)) + " records (retries so far " + str(retries)+") " + str(errors_seen))
            time.sleep(BACKOFF_S)
            self.send_to_kinesis(new_records, retries+1)
            # "Records": [ 
            #    { 
            #        "ErrorCode": "string",
            #        "ErrorMessage": "string",
            #        "SequenceNumber": "string",
            #        "ShardId": "string"
            #    }
    
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


