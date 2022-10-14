#!/usr/bin/env python
r"""
Timestream_Worker
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
import os, sys
import queue    # Multiprocessing uses this internally, and returns queue.Empty exception
import traceback
import setproctitle, multiprocessing

import boto3 # AWS library
from botocore.config import Config

HTTP_OK = 200

TIMESTREAM_MAX_MESSAGES_PER_POST = 100     # Timestream requirement
REPORT_EVERY_S = 1
BACKOFF_S = 0  # How long to wait when AWS says its under-provisioned (set to 0 to force AWS to just cope!)
MAX_EXPLODE = 1_000_000

POLL_PERIOD_S = 0.1 # How often the workers poll for new work

g_id_time = {}    # Unique combinations of ID and timestamp (to check if we ever repeat)

### This code is executed in the target process(es), so must not refer to Synth environment

def child_func(qtx, qrx):   # qtx is messages to send, qrx is feedback to Synth
    setproctitle.setproctitle(multiprocessing.current_process().name)
    (params, logfile_abspath) = qtx.get()    # First item sent is a dict of params
    worker = Worker(params)
    while True:
        try:
            v = qtx.get(timeout=POLL_PERIOD_S)
            if v is None:
                logging.info("Worker "+str(os.getpid()) + " requested to exit")
                return
            worker.enqueue(v)
            worker.note_input_queuesize(qtx.qsize())
        except queue.Empty:
            pass
        except Exception as e:
            logging.error("Error in worker "+str(os.getpid())+": "+str(e))  # Force errors into logging subsystem
            logging.error(traceback.format_exc())
            raise

        result = worker.tick()
        if result:
            qrx.put(result)

class Worker(): 
    def __init__(self, params):
        # logging.info("Timestream Worker "+str(os.getpid())+" initialising with params "+str(params))
        self.params = params

        if "setenv" in params:
            for (key, value) in params["setenv"].items():
                # logging.info("SETENV "+key+" "+value)
                os.environ[key] = value

        if "profile_name" in self.params:   # For some reason I don't understand, if you specify the profile_name here then auth fails (even if you've specified it as an environment variable). So only specify as an environment variable.
            session = boto3.Session(self.params["profile_name"])
        else:
            session = boto3.Session()

        # if not session.get_credentials().secret_key:  # With very high parallelism this occasionally fails
        #    logging.error("Timestream worker sees no AWS secret key, so this isn't going to work")

        attempts = 0
        while True:
            try:
                self.write_client = session.client('timestream-write', config=Config(read_timeout=20, max_pool_connections = 5000, retries={'max_attempts': 100}))
                break
            except:
                if attempts > 1:
                    logging.warning("Failed to create write client, this sometimes happens under heavy load, attempt "+str(attempts))
            attempts += 1

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

    def _enqueue(self, properties):
        global g_id_time

        dimensions = [{ "Name" : "$id", "Value" : properties["$id"], "DimensionValueType" : "VARCHAR" }]    # TODO: Add any other metadata here
        t = str(int(properties["$ts"] * 1000))

        id_time = properties["$id"] + "-" + str(t)
        if id_time in g_id_time:
            logging.error("Already seen this ID & time combination " + str(id_time))
            logging.error("Original " + str(g_id_time[id_time]))
            logging.error("New  "+str(properties))
            assert(False)
        else:
            g_id_time[id_time] = properties.copy()

        measures = []
        for (k,v) in properties.items():
            if k not in ["$id", "$ts"]:
                measures.append( { "Name" : k, "Value" : str(v), "Type" : 'DOUBLE' } )  # TODO: Other types
        record = { "Dimensions" : dimensions, "MeasureName" : "multimeasure", "MeasureValues" : measures, "MeasureValueType" : "MULTI", "Time" : t } 
        self.queue.append(record)

    def enqueue(self, properties):
        if self.params["explode_factor"] == 1:
            self._enqueue(properties)
        else:
            prop_copy = properties.copy()
            the_id = properties["$id"]
            for n in range(self.params["explode_factor"]):
                prop_copy["$id"] = the_id + "_%06d" % n
                self._enqueue(prop_copy)

    def tick(self):
        # Transmits waiting messages, and occasionally returns stats
        result = None

        t =  time.time()
        if t > self.last_report_time + REPORT_EVERY_S :
            elap = t - self.start_time
            tDelta = 0
            if len(self.queue) > 0:
                tDelta = int(time.time() - int(self.queue[0]["Time"])/1000.0)   # Sample the timestamp in next message (which will be first to send, so reasonable)

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

        # logging.info(str(len(self.queue))+" records to send")
        while len(self.queue) > 0:  # Will result in last send being a partial block - not best efficiency, but alternative is to leave a partial block unsent (perhaps forever)
            tA = time.time()
            if len(self.queue) < TIMESTREAM_MAX_MESSAGES_PER_POST:
                logging.warning("Posting less than max number of records")
            num = min(TIMESTREAM_MAX_MESSAGES_PER_POST, len(self.queue))
            self.send_to_timestream(self.queue[0:num])

            self.num_blocks_sent_ever += 1
            self.num_blocks_sent_recently += 1
            self.queue = self.queue[num:]
            tB = time.time()
            # logging.info("Sending "+str(num)+" records took "+str(tB-tA))
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

    def send_to_timestream(self, records, retries=0):
        # logging.info("Send to timestream " + str(len(records)) + "\n" + str(records))
        success = False
        while not success:
            try:
                result = self.write_client.write_records(DatabaseName=self.params["database_name"], TableName=self.params["table_name"],
                                                Records=records, CommonAttributes={})
                status = result['ResponseMetadata']['HTTPStatusCode']
                if status == HTTP_OK:
                    success = True
                else:
                    logging.warning("WriteRecords Status: " + status)
            except self.write_client.exceptions.RejectedRecordsException as err:
                logging.warning("Worker "+str(os.getpid())+": Some records were rejected")
                logging.warning(str(err))
                for rr in err.response["RejectedRecords"]:
                    idx = rr["RecordIndex"]
                    reason = rr["Reason"]
                    logging.error("Rejected Index " + str(idx) + ": " + str(reason) + ". Record: "+str(records[idx]))
                raise

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


