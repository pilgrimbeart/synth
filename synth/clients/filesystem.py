#!/usr/bin/env python
#
# Dump events to the filesystem
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

import logging
import json
from clients.client import Client

# We don't know a-priori which properties we'll encounter,
# but we need to write a CSV file which includes a column header
# for each property, so we accumulate everything and write at the end.
# <time> and <device_id> are concatenated to make our key

SEP = "!"

class Filesystem(Client):
    def __init__(self, params):
        logging.info("Starting filesystem client with params "+str(params))
        self.params = params
        self.postQueue = {} # A dict of events. Each contains a list of (prop,val) pairs

    def add_device(self, device_id, time, properties):
        self.update_device(device_id, time, properties)

    def update_device(self, device_id, time, properties):
        # logging.info("postDevice "+str(device))
        newProps = []

        # Construct list of (prop,value)
        for k in properties.keys():
            if k not in ["$id","$ts"]:
                newProps.append( (k, properties[k]) )
        # logging.info("Property list is "+str(newProps))

        # Insert
        key = str(time) + SEP + str(device_id)
        if key in self.postQueue:
            existingProps = self.postQueue[key] # Extend list if it already exists
        else:
            existingProps = []
        existingProps.extend(newProps)

        # logging.info("Final property list is "+str(key)+" : " +str(existingProps))
        self.postQueue[key] = existingProps
        return True

    def get_device(self):
        return None

    def get_devices(self):
        return None

    def delete_device(self):
        pass
    
    def enter_interactive(self):
        pass

    def tick(self):
        pass
    
    def flush(self):
        # Collect all property names
        props = []
        for k in self.postQueue.keys():
            for (p,v) in self.postQueue[k]:
                if p not in props:
                    props.append(p)
        props.sort()

        # Write column headers
        f = open("../synth_logs/"+self.params["filename"]+".csv","wt")
        f.write("$ts,$id,")
        for p in props:
            f.write(p+",")
        f.write("\n")

        # Write time series
        for k in sorted(self.postQueue.keys()):
            (t,i) = k.split(SEP)
            f.write(t+","+i+",")
            for propName in props:  # For every column
                found=False
                for (p,v) in self.postQueue[k]: # If we have a value, write it
                    if p==propName:
                        f.write(str(v)+",")
                        found=True
                        break
                if not found:
                    f.write(",")
            f.write("\n")

        f.close()
        
        return
