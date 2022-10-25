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

REPORT_EVERY_S = 60

class WorkerParent():   # Create a worker, and communicate with it
    def __init__(self, instance_name, params, logfile_abspath):
        self.merge_buffer = {}  # Messages, keyed by ID

        self.qtx = MP_Queue()
        self.qrx = MP_Queue()
        assert "type" in params, "Client params must specify a type=kinesis/timestream"
        if params["type"] == "kinesis":
            child_func = kinesis_worker.child_func
        elif params["type"] == "timestream":
            child_func = timestream_worker.child_func
        else:
            assert False, "Invalid option for type param in client params"
        self.p = MP_Process(target=child_func, args=(self.qtx, self.qrx), name="synth_worker " + instance_name)
        self.p.start()
        self.qtx.put( (params, logfile_abspath) ) # First item on queue is parameters

        self.stats = None   # Updated periodically by child processes
        self.old_stats = None  # Updated periodically by parent

        self.merge_buffer_timestamp = 0

    def purge_merge_buffer(self, t):
        # logging.info("Sending merge buffer which is " + str(len(self.merge_buffer)) + " items")
        for (dev, props) in self.merge_buffer.items():
            # logging.info("    " + str(props))
            self._send(props)
        self.merge_buffer = {}
        self.merge_buffer_timestamp = t
    
    def enqueue(self, properties):
        device_id = properties["$id"]
        t = properties["$ts"]
 
        # If time has advanced, emit merge buffer
        if t != self.merge_buffer_timestamp:
            # logging.info("client_workers: time has advanced, so sending merge buffer")
            self.purge_merge_buffer(t)
            
        # Add to merge buffer
        if device_id in self.merge_buffer:
            if merge_test.ok(self.merge_buffer[device_id], properties):
                self.merge_buffer[device_id].update(properties)
        else:   
            self.merge_buffer[device_id] = properties

    def tick(self, t):
        if t > self.merge_buffer_timestamp:
            # logging.info("client_workers:tick() time has advanced, so sending merge buffer")
            self.purge_merge_buffer(t)

        while True: # Grab all available stats feedback
            try:
                stats = self.qrx.get(timeout=0)
                self.stats = stats
            except queue.Empty:
                break

    def _send(self, data, check_alive=True):  # Don't use this directly if you want message merging
        self.qtx.put(data)
        if check_alive:
            if not self.p.is_alive():
                logging.error("Worker " + str(self.p.pid) + " has died - so terminating")
                assert(False)

    def wait_until_stopped(self):
        logging.info("Worker " + str(self.p.pid) + " asked to stop")
        try:
            while True: # Flush the queue (so our stop signal gets there ASAP)
                self.qtx.get(timeout=0) #
        except:
            pass
        self._send(None, check_alive=False)    # Signal to stop (OK if already dead!)
        # logging.info("Waiting for worker " + str(self.p.pid) + " to stop")
        self.p.join()
        logging.info("...stopped")


start_time = 0
last_report = 0

def output_stats(workers):
    global start_time, last_report
    if start_time == 0:
        start_time = time.time()

    if time.time() < last_report + REPORT_EVERY_S:
        return
    last_report = time.time()

    tot_blocks = 0
    new_blocks = 0
    num_workers = 0
    min_queue_size = 1e30
    max_queue_size = 0
    max_t_delta = 0
    empty_workers = 0
    slowest_post = 0
    post_stats = [0,0,0,0,0]
    total_post_latency = 0
    for w in workers:
        if w.stats:
            num_workers += 1
            tot_blocks += w.stats["num_blocks_sent_ever"]
            new_blocks += w.stats["num_blocks_sent_ever"]
            max_queue_size = max(max_queue_size, w.stats["max_queue_size_recently"])
            min_queue_size = min(min_queue_size, w.stats["max_queue_size_recently"])
            slowest_post = max(slowest_post, w.stats["slowest_post_recently"])
            if w.stats["max_queue_size_recently"] == 0:
                empty_workers += 1
            max_t_delta = max(max_t_delta, w.stats["t_delta"])
            for i in range(len(post_stats)):
                post_stats[i] += w.stats["post_stats"][i]
            total_post_latency += w.stats["total_post_latency"]
        if w.old_stats:
            new_blocks -= w.old_stats["num_blocks_sent_ever"]
        w.old_stats = w.stats
     
    logging.info("T+ "+str(int(time.time()-start_time)) + " " +
                str(num_workers)+" workers " +
                str(tot_blocks) + " posts " +
                str(new_blocks/REPORT_EVERY_S) + " posts/s (" + str(REPORT_EVERY_S) + "s) " +
                "%1.1f" % (slowest_post) + "s slowest " +
                str(post_stats) + " " +
                str(int(total_post_latency)) + "tpl " +
                str((min_queue_size,max_queue_size)) + "Q " +
                str(empty_workers)+" empty w's, " +
                str(max_t_delta)+" max_t_delta"
                )
