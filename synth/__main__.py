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
    engine_configuration = {'type': 'pause', 'max': 100}
    clients_configuration = {
        'type': 'stack',
        'clients': [
            {'type': 'console', 'name': 'first'},
            {'type': 'console', 'name': 'second'}
        ]
    }
    estate_configuration = [
        {'type': 'simple', 'id': 'A', 'delay': 0, 'initial': 1, 'increment': 2, 'interval': 3},
        {'type': 'simple', 'id': 'B', 'delay': 4, 'initial': 5, 'increment': 6, 'interval': 7},
    ]

    # build stack.
    engine = importer \
        .get_class('engine', engine_configuration.get('type', 'step')) \
        (engine_configuration)
    client = importer \
        .get_class('client', 'stack') \
        (clients_configuration)
    importer.get_class('device', 'simple') \
        .build_estate(estate_configuration, engine, client)

    # start simulation.
    logger.info("Starting simulation.")
    engine.start_event_loop()


if __name__ == "__main__":
    main()
