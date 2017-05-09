#!/usr/bin/env python

# Standalone program which spawns new Synth processes
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


<<<<<<< HEAD:synth/server/spawner.py
import subprocess
import time
import traceback
=======
import zeromq_rx, time, subprocess, sys
>>>>>>> 60686512731fc02824217555eac422e222efc148:spawner.py
from datetime import datetime
from synth.server import zeromq_rx


def spawnIt(params):
    print datetime.now(), "Got", str(params)
    if not "action" in params:
        print datetime.now(), "Got",str(params),"(ignoring)"
        sys.stdout.flush()
        return
    if params["action"] != "spawn":
        print datetime.now(), "Got",str(params),"(ignoring)"
        sys.stdout.flush()
        return
    print datetime.now(), "Spawning "+str(params)
    sys.stdout.flush()
    (dpKey, dpApi) = (params["key"],params["api"])
    
    try:
        command = "./runSynth devicepilot_key="+dpKey+" devicepilot_api="+dpApi+" instance_name=devicepilot_key="+dpKey+" UserDemo"
        print datetime.now(), "Command:",command
        sys.stdout.flush()
        result = subprocess.call(command, shell=True)
        # CAUTION: shell=True makes us vulnerable to injection attacks, so we trust that the ZeroMQ publisher has sanitised inputs
        print "Result:", result
    except Exception as e:
        print "Error in spawn: " + str(e)
        print traceback.format_exc()
    print "Result:", result


if __name__ == "__main__":
    print datetime.now(), "Starting Spawner"
    zeromq_rx.init(spawn_it)
    sys.stdout.flush()
    while True:
        time.sleep(1)
