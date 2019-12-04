#!/usr/bin/env python
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
 
import sys, threading, logging, traceback, json, time
import zmq

ZEROMQ_PORT = 5556
ZEROMQ_BUFFER = 100000

# Socket to talk to server
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect ("tcp://localhost:%s" % ZEROMQ_PORT)
socket.set_hwm(ZEROMQ_BUFFER)

topicfilter = ""    # ZeroMQ will do filtering for us, but only on client side
socket.setsockopt(zmq.SUBSCRIBE, topicfilter.encode('ascii'))

def rxThread(callback):
    logging.info("ZeroMQ rx thread started")
    while True:
        try:
            string = socket.recv()  # { "action" : {"event"|"spawn"} ... }
            logging.info("Received on ZeroMQ: " + str(string))
            params = json.loads(string)
            callback(params)
        except Exception as e:
            logging.error("Error in ZeroMQ thread: "+str(e))
            logging.error(traceback.format_exc())
            time.sleep(1)    # Avoid 100% CPU in case socket.recv() dies

    logging.critical("ZeroMQ rx thread exiting")
    
def init(callback):
    logging.info("Starting ZeroMQ rx thread")
    t = threading.Thread(target=rxThread, kwargs={"callback":callback})
    t.daemon = True
    t.start()
