"""
GET /?<magickey>
----------------
Return a basic page listing all running Synth processes and free memory.
For security this must be accompanied by a magic key matching the contents of the file ../synth_certs/magickey

GET /spawn?devicepilot_key=XXX&devicepilot_api=staging
------------------------------------------------------
Spawn a new instance of Synth, with these two specific parameters set. The UserDemo scenario is run.
The instance_name is set to be "devicepilot_key=XXX" since that is assumed to be unique.

GET /is_running?devicepilot_key=XXX&devicepilot_api=staging
-----------------------------------------------------------
Find whether a specific instance of Synth (identified by its key) is still running. Return a JSON struct with active=true/false.

GET /plots/<filename>
---------------------
Return a plot generated by the Expect device function

POST /event
-----------
This causes an inbound device event to be asynchronously generated, to a specific device on a specific Synth instance. 
The header of the web request must contain the following::

    Key : <web_key parameter> 
    Instancename : <instance_name parameter>

The body of the web request must contain a JSON set include the following elements::

    "deviceId" : "theid"
    "eventName" : "replace_battery" | "upgradeFirmware" | "factoryReset"
    "arg" : "0.7" - optional argument only relevant for some eventNames

If defining a Webhook Action in DevicePilot to create a Synth event, the device ID will be automatically filled-out if you define it as {device.$id},
resulting in an action specification which looks something like this::

    method: POST
    url: https://synthservice. com/event
    headers: { "Key":"mywebkey", "Instancename" : "OnProductionAccountUser" }
    body: { "deviceId" : "{device.$id}", "eventName" : "upgadeFirmware", "arg":"0.7"}
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

from flask import Flask, request, abort
from flask_cors import CORS, cross_origin
import multiprocessing, subprocess
import json, time, logging, sys, re
import zmq # pip install pyzmq-static

WEB_PORT = 443 # HTTPS. If < 1000 then this process must be run with elevated privileges
ZEROMQ_PORT = 5556

zeromqSocket = None # Global, but we create it in the app context so we don't have inter-process issues
lastPingTime = multiprocessing.Value('d', time.time())
PING_TIMEOUT = 60*5 # We expect to get pinged every N seconds

app = Flask(__name__)
CORS(app)   # Make Flask tell browser that cross-origin requests are OK

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def createSocket():
    global zeromqSocket
    logging.info("Initialising ZeroMQ to publish to port "+str(ZEROMQ_PORT))
    context = zmq.Context()
    zeromqSocket = context.socket(zmq.PUB)
    zeromqSocket.bind("tcp://*:%s" % ZEROMQ_PORT)

@app.route("/event", methods=['POST','GET'])
def event():
    """Accept an incoming event and route it to a Synth instance."""
    global zeromqSocket
    if zeromqSocket == None:
        createSocket()

    logging.info("Got web request to /event")
    h = {}
    for (key,value) in request.headers:
        h[key] = value
    packet = {
        "action" : "event",
        "headers" : h,
        "body" : request.get_json(force=True)
        }
    logging.info(str(packet))
    zeromqSocket.send(json.dumps(packet))
    return "ok"

def getAndCheckKey(req):
    if not "devicepilot_key" in req.args:
        logging.error("Missing devicepilot_key argument")
        return None

    dpKey = req.args["devicepilot_key"]

    # Defend against injection attack
    if len(dpKey) != 32:
        logging.error("Bad key length")
        return None
    if re.search(r'[^a-z0-9]', dpKey):
        logging.error("Bad key characters")
        return None

    return dpKey

def getAndCheckApi(req):
    """Stop external users passing-in any old URL."""
    if not "devicepilot_api" in req.args:
        dpApi = "api"
    else:
        dpApi = req.args["devicepilot_api"]

    # Defend against injection attack
    if not dpApi in ["api","api-staging","api-development"]:
        dpApi = "api"

    return "https://"+dpApi+".devicepilot.com"
    
@app.route("/spawn", methods=['GET'])
def spawn():
    """Start a new Synth instance."""
    global zeromqSocket
    if zeromqSocket == None:
        createSocket()

    logging.info("Got web request to /spawn")
    dpKey = getAndCheckKey(request)
    if dpKey==None:
        abort(403)

    dpApi = getAndCheckApi(request)

    packet = { "action" : "spawn", "key" : dpKey, "api" : dpApi }
    zeromqSocket.send(json.dumps(packet))
    logging.info("Sent packet "+str(packet))
    time.sleep(1)   # If client next immediately tests <is_running>, this will vastly increase chances of that working
    return "ok"

@app.route("/plots/<filename>", methods=['GET'])
def plots(filename):
    """Serve plots from special directory"""
    logging.info("Got web request to "+str(request.path)+" so filename is "+str(filename))

    if re.search(r'[^A-Za-z0-9.]', filename):
        for c in filename:
            logging.info(str(ord(c)))
        logging.info("Bad characters")
        abort(400)

    if ".." in filename:
        logging.info("Illegal .. in pathname")
        abort(400)

    try:
        f=open("../synth_logs/plots/"+filename).read()
    except:
        logging.warning("Can't open file")
        return ("Can't open that file")
    return f

@app.route("/is_running")
def isRunning():
    logging.info("Got web request to /is_running")
    dpKey = getAndCheckKey(request)
    if dpKey==None:
        abort(403)

    try:
        x = subprocess.check_output("ps uax | grep 'python' | grep 'devicepilot_key=" + dpKey + "' | grep -v grep", shell=True)
    except:
        return '{ "active" : false }'
    return '{ "active" : true }'

@app.route("/")
def whatIsRunning():
    """We expect Pingdom to regularly ping this route to reset the heartbeat."""
    global lastPingTime
    global zeromqSocket
    if zeromqSocket == None:
        createSocket()

    logging.info("Got web request to /")
    lastPingTime.value = time.time()
    magicKey=open("../synth_certs/webkey","rt").read().strip()
    if magicKey not in request.args:
        abort(403)
    zeromqSocket.send(json.dumps({"action": "ping"}))   # Propagate pings into ZeroMQ for liveness logging throughout rest of system
    try:
        x = subprocess.check_output("ps uax | grep 'python' | grep -v grep", shell=True)
        x += "<br>"
        x += subprocess.check_output("free -m", shell=True)
    except:
            return "Nothing"
    return "<pre>"+x.replace("\n","<br>")+"</pre>"
        
def startWebServer():
    """Doing app.run() with "threaded=True" starts a new thread for each incoming request, improving crash resilience
       By default Flask serves to 127.0.0.1 which is local loopback (not externally-visible), so use 0.0.0.0 for externally-visible
       We run entire Flask server as a distinct process so we can terminate it if it fails (can't terminate threads in Python)"""
    logging.info("Starting Flask web server process, listening on port "+str(WEB_PORT))    # If port < 1000 then this process must be run with elevated privileges
    p = multiprocessing.Process(target=app.run, kwargs={"threaded":True, "host":"0.0.0.0", "port":WEB_PORT, "ssl_context":('../synth_certs/ssl.crt', '../synth_certs/ssl.key')})
    p.daemon = True
    p.start()
    return p

if __name__ == "__main__":
    server = startWebServer()
    while True:
        time.sleep(1)
        if time.time()-lastPingTime.value > PING_TIMEOUT:
            logging.critical("Web server not detecting pings - restarting")
            server.terminate()
            server = startWebServer()
            time.sleep(60)
