"""JSONwriter
Writes events to JSON files, segmenting on max size"""

import logging
import time
import json_quick

DEFAULT_DIRECTORY = "../synth_logs/"
DEFAULT_MAX_EVENTS_PER_FILE = 100000    # FYI 100,000 messages is max JSON file size that DP can ingest (if that's where you end-up putting these files)

class Stream():
    """Write properties into JSON files, splitting by max size.
       If you access .files_written property then call close() first"""
    def __init__(self, filename, directory = DEFAULT_DIRECTORY, file_mode="wt", max_events_per_file = DEFAULT_MAX_EVENTS_PER_FILE):
        self.file_path = directory + filename
        self.file_mode = file_mode
        self.max_events_per_file = max_events_per_file
        self.file = None
        self.files_written = []
        self.file_count = 1

    def write_event(self, properties):
        self.check_next_file()
        jprops = properties.copy()
        jprops["$ts"] = int(jprops["$ts"] * 1000) # Convert timestamp to ms as that's what DP uses internally in JSON files
        if self.events_in_this_file > 0:
            self.file.write(",\n")
        s = json_quick.dumps(jprops)
        self.file.write(s)

    def move_to_next_file(self):
        """Move to next json file"""
        if self.file is not None:
            self.close()

        filename = self.file_path + "%05d" % self.file_count + ".json"
        logging.info("Starting new logfile " + filename)
        self.file = open(filename, self.file_mode, 0)
        self.file.write("[\n")
        self.events_in_this_file = 0
        self.files_written.append(filename)

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
            # logging.info("Closing JSON file")
            self.file.write("\n]\n")
            self.file.close()
            self.file = None
            self.file_count += 1
           
