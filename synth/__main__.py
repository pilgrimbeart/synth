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

from synth.common import importer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Synth instance started.")

    # get configuration.
    engine_configuration = {'type': 'step'}
    client_configuration = {
        'type': 'stack',
        'clients': [
            {'type': 'console', 'name': 'first'},
        ]
    }
    # device_configuration = {
    #     'type': 'delay',
    #     'devices': [
    #         {'device': {'type': 'simple', 'id': 'A', 'initial': 1, 'increment': 2, 'interval': 'PT3H'}},
    #         {'delay': 'PT4H',
    # 'device': {'type': 'simple', 'id': 'B', 'initial': 5, 'increment': 6, 'interval': 'PT7H'}},
    #     ]
    # }
    device_configuration = {
        'type': 'blb',
        'id': 'blb_test'
    }

    # build stack.
    engine = importer \
        .get_class('engine', engine_configuration['type'])(engine_configuration)
    client = importer \
        .get_class('client', client_configuration['type'])(client_configuration)
    importer\
        .get_class('device', device_configuration['type'])(device_configuration, engine, client)

    # start simulation.
    logger.info("Starting simulation.")
    engine.start_event_loop()


if __name__ == "__main__":
    main()
