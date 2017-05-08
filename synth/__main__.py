#!/usr/bin/env python

# Generate and simulate a virtual device estate.

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

from synth.simulation.engine import Engine
# from synth.clients.client import Client
from synth.clients.console import Console
# from synth.devices.device import Device
from synth.devices.simple import Simple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Synth instance started.")

    # get configuration.
    engine_configuration = {}
    clients_configuration = [{}]
    estate_configuration = [
        {'id': 'A', 'delay': 0, 'initial': 1, 'increment': 2, 'interval': 3},
        {'id': 'B', 'delay': 4, 'initial': 5, 'increment': 6, 'interval': 7},
    ]

    # build stack.
    engine = Engine() # engine_configuration)
    client_stack = Console(clients_configuration)
    Simple.build_estate(estate_configuration, engine, client_stack)

    # start simulation.
    logger.info("Starting simulation.")
    engine.start_event_loop()

if __name__ == "__main__":
    main()