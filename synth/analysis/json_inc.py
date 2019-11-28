"""
    JSON_INC
    Read and write JSON file file batches incrementally
    File format is a subset of legal JSON:
        [
                { ... },    # Max 100000 of these
                { ... }
        ]

"""
#
#
# Copyright (c) 2019 DevicePilot Ltd.
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

import sys, os, glob
import json
import logging

MESSAGES_PER_FILE = 1E5

class Reader():
    """Open a JSON file and read it line-by-line"""
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_handle = open(file_path, "rt")
        L = self.file_handle.readline().strip()
        assert L == "[", "Expected first line to be [ but it was "+L
        self.props = None   # The current line of the JSON file
        self.consume_row()  # Consume the first data row

    def consume_row(self):
        L = self.file_handle.readline().strip()
        if L == "]":
            logging.info("Reached end of file "+self.file_path)
            self.props = None
        elif len(L) == 0:
            pass    # Blank line
        else:
            # logging.info(str(self.file_path) + ":" + str(L))
            self.props = json.loads(L.strip(","))   # All but last line will have a trailing comma because elements in a list

    def at_eof(self):
        return self.props is None

class Writer():
    """Write JSON files to disk as a series of files of max size"""
    def __init__(self, filestem):
        self.filestem = filestem
        self.file_count = 0
        self.message_count = 0
        self.open()

    def open(self):
        filename = self.filestem + "%05d.json" % self.file_count
        logging.info("Writing "+filename)
        self.out = open(filename, "wt")
        self.out.write("[\n")
        self.first_out = True

    def close(self):
        self.out.write("\n]")
        self.out.close()
        self.file_count += 1

    def write(self, props):
        if not self.first_out:
            self.out.write(",\n")
        self.first_out = False
        self.out.write(json.dumps(props, sort_keys=True))

        self.message_count += 1
        if self.message_count >= MESSAGES_PER_FILE:
            self.close()
            self.open()
            self.message_count = 0

