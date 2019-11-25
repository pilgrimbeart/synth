"""
    Given a set of .json files, this merges them in time order.
    Each file must contain a JSON list of messages, of the form:
        [
                { "$id" : 123, "$ts" : 456, "other" : "stuff" },
                { "$id" : 234, "$ts" : 567, "more" : "stuff" }
        ]
    Each message is a dict containing at least a $id and $ts field, already sorted by rising $ts.
    One line per message.
"""

import sys, os, glob
import json
import logging

MESSAGES_PER_FILE = 1E5

def find_all_properties(messages):
    properties = []
    for message in messages:
        for prop in message:
            if prop not in ["$ts", "$id"]:  # Ignore these
                if prop not in properties:
                    properties.append(prop)
    return sorted(properties)   # Keeping the order consistent just helps with readability

class Incremental_json():
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
        else:
            self.props = json.loads(L.strip(","))   # All but last line will have a trailing comma because elements in a list

    def at_eof(self):
        return self.props is None

class Output_file_series():
    def __init__(self, filestem):
        self.filestem = filestem
        self.file_count = 0
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

def merge_json_files(file_list, output_filestem):

    def close_output_file():
        global out, file_count

    out = Output_file_series(output_filestem)
    message_count = 0

    logging.info("Merging files "+str(file_list))

    # Open all files
    inc_files = []
    for f in file_list:
        inc_files.append(Incremental_json(f))

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

        message_count += 1
        if message_count >= MESSAGES_PER_FILE:
            out.close()
            out.open()
            message_count = 0

    out.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Merge all the CSV files together
    files = []
    for f in sys.argv[1:]:
        files.extend(glob.glob(f))
    merge_json_files(files, "merge")

