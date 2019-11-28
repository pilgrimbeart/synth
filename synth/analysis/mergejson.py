"""
    MERGEJSON - command-line utility

    Given a set of .json files, this merges them in time order.
    Each file must contain a JSON list of messages, of the form:
        [
                { "$id" : 123, "$ts" : 456, "other" : "stuff" },
                { "$id" : 234, "$ts" : 567, "more" : "stuff" }
        ]
    Each message is a dict containing at least a $id and $ts field, already sorted by rising $ts.
    One line per message.
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
import json_inc
import logging

def merge_json_files(file_list, output_filestem):

    out = json_inc.Writer(output_filestem)

    logging.info("Merging files "+str(file_list))

    # Open all files
    inc_files = []
    for f in file_list:
        inc_files.append(json_inc.Reader(f))

    # Scan along files, consuming them in time order
    while True:
        # Reached end of all files?
        something_to_do = False
        for f in inc_files:
            if not f.at_eof():
                something_to_do = True
        if not something_to_do:
            break

        # First earliest timestamp
        earliest_ts = None
        earliest_file = None
        for f in inc_files:
            if not f.at_eof(): # Haven't reached the end of this file
                if earliest_ts is None:
                    # logging.info(str(f.props))
                    earliest_ts = f.props["$ts"] 
                    earliest_file = f
                else:
                    if f.props["$ts"] < earliest_ts:
                        earliest_ts = f.props["$ts"]
                        earliest_file = f

        out.write(earliest_file.props)
        earliest_file.consume_row()

    out.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Merge all the CSV files together
    files = []
    for f in sys.argv[1:]:
        files.extend(glob.glob(f))
    merge_json_files(files, "merge")

