"""JSONwriter
Writes events to JSON files, segmenting on max size"""

import logging
import json

DEFAULT_DIRECTORY = "../synth_logs/"
DEFAULT_MAX_EVENTS_PER_FILE = 10000

class Stream():
    def __init__(self, filename, directory = DEFAULT_DIRECTORY, file_mode="wt", max_events_per_file = DEFAULT_MAX_EVENTS_PER_FILE):
        self.file_path = directory + filename
        self.file_mode = file_mode
        self.max_events_per_file = max_events_per_file
        self.file = None

    def write_event(self, properties):
        self.check_next_file()
        jprops = properties.copy()
        jprops["$ts"] = int(jprops["$ts"] * 1000) # Convert timestamp to ms as that's what DP uses internally in JSON files
        if self.events_in_this_file > 0:
            self.file.write(",\n")
        self.file.write(json.dumps(jprops, sort_keys=True))

    def move_to_next_file(self):
        """Move to next json file"""
        if self.file is None:
            self.file_count = 1
        else:
            self.close()
            self.file_count += 1

        filename = self.file_path + "%05d" % self.file_count + ".json"
        logging.info("Starting new logfile " + filename)
        self.file = open(filename, self.file_mode, 0)
        self.file.write("[\n")
        self.events_in_this_file = 0

    def check_next_file(self):
        """Check if time to move to next json file"""
        if self.file is None:
            self.move_to_next_file()
            return
        if self.events_in_this_file >= self.max_events_per_file-1:
            self.move_to_next_file()
            return
        self.events_in_this_file += 1

    def close(self):
        if self.file is not None:
            self.file.write("\n]\n")
            self.file.close()
            self.file = None

