"""
    zerome_tx.py
    Uses ZeroMQ to create a machine-wide bus with standard message format
"""

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
#
# WARNING: it appears that if you bind ZMQ to a socket on multiple processes
# then the second one fails *silently*! So don't call socket_send() from the parent
# process, or Flask's ZMQ sends will all fail silently.
#
# By convention, packets are JSON dicts, containing at least { "action" : <action> }
import time
import logging
import threading
import sys
import zmq # pip install pyzmq-static
import json
import traceback

ZEROMQ_PORT = 5556
ZEROMQ_BUFFER = 100000

g_zeromq_socket = None # Global, protected via g_lock
g_lock = None

g_emit_logging = True
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def create_socket():
    global g_emit_logging
    global g_zeromq_socket
    if g_emit_logging:
        logging.info("Initialising ZeroMQ to publish to TCP port "+str(ZEROMQ_PORT)+ " with buffer size " + str(ZEROMQ_BUFFER))
    context = zmq.Context()
    g_zeromq_socket = context.socket(zmq.PUB)
    g_zeromq_socket.bind("tcp://*:%s" % ZEROMQ_PORT)
    g_zeromq_socket.set_hwm(ZEROMQ_BUFFER)

def socket_send(json_msg):
    global g_lock, g_zeromq_socket
    t = time.time()
    
    g_lock.acquire()
    try:
        if g_zeromq_socket == None:
            create_socket()
            time.sleep(1)   # It seems that if you send a message immediately after creating socket, it gets lost
        g_zeromq_socket.send(json.dumps(json_msg).encode('ascii'))
    except:
        logging.error("ERROR in socket_send")
        logging.critical(traceback.format_exc())
        raise
    finally:
        g_lock.release()

    elapsed = time.time() - t
    if elapsed > 0.1:
        logging.error("****** SLOW POSTING *******")
        logging.error("Took "+str(elapsed)+"s to post event")
    
def init(emit_logging=True):
    global g_emit_logging
    global g_lock
    g_emit_logging = emit_logging
    g_lock = threading.Lock()
