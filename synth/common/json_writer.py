"""JSONwriter
Writes events to JSON files, segmenting on max size"""

import os, pathlib, shutil
import logging
import time
from datetime import datetime
from . import json_quick
from . import merge_test

TEMP_DIRECTORY = "/tmp/synth_json_writer/"  # We build each file in a temporary directory, then move when it's finished (so that anyone watching the destination directory doesn't ever encounter partially-written files
DEFAULT_DIRECTORY = "../synth_logs/"
DEFAULT_MAX_EVENTS_PER_FILE = 100000    # FYI 100,000 messages is max JSON file size that DP can ingest (if that's where you end-up putting these files)

class Stream():
    """Write properties into JSON files, splitting by max size.
       If you access .files_written property then call close() first"""
    def __init__(self, filename, directory = DEFAULT_DIRECTORY, file_mode="wt",
            max_events_per_file = DEFAULT_MAX_EVENTS_PER_FILE, merge = False,
            ts_prefix = False, messages_prefix = False):
        pathlib.Path(TEMP_DIRECTORY).mkdir(exist_ok=True)   # Ensure temp directory exists

        self.target_directory = directory
        self.filename_root = filename
        self.file_mode = file_mode
        self.max_events_per_file = max_events_per_file
        self.merge = merge
        self.ts_prefix = ts_prefix
        self.messages_prefix = messages_prefix

        self.file = None
        self.filename = None
        self.files_written = []
        self.file_count = 1
        self.last_event = {}    # Used to merge messages
        self.first_timestamp = None
 
    def _write_event(self, properties):
        self.check_next_file()
        jprops = properties.copy()
        if self.first_timestamp is None:
            self.first_timestamp = jprops["$ts"]
        jprops["$ts"] = int(jprops["$ts"] * 1000) # Convert timestamp to ms as that's what DP uses internally in JSON files
        s = json_quick.dumps(jprops)
        if self.events_in_this_file > 0:
            s = ",\n" + s
        self.file.write(s)

    def write_event(self, properties):
        if not self.merge:
            self._write_event(properties)
            return

        if len(self.last_event) == 0:
            self.last_event = properties
            return

        if merge_test.ok(self.last_event, properties):
            self.last_event.update(properties)
        else:
            self._write_event(self.last_event)
            self.last_event = properties   

    def move_to_next_file(self):
        """Move to next json file"""
        if self.file is not None:
            self._close()

        self.filename = self.filename_root + "%05d" % self.file_count + ".json"
        logging.info("Starting new logfile " + self.filename)
        self.file = open(TEMP_DIRECTORY + self.filename, self.file_mode)  # No-longer unbuffered as Python3 doesn't support that on text files
        self.file.write("[\n")
        self.events_in_this_file = 0

    def check_next_file(self):
        """Check if time to move to next json file"""
        if self.file is None:
            self.move_to_next_file()
            return
        self.events_in_this_file += 1
        if self.events_in_this_file >= self.max_events_per_file:
            self.move_to_next_file()
            return

    def _close(self):
        if self.file is not None:
            # logging.info("Closing JSON file")
            self.file.write("\n]\n")
            self.file.close()
            if self.ts_prefix:
                dt = datetime.fromtimestamp(self.first_timestamp)
                prefix = dt.strftime("%Y-%m-%dT%H-%M-%S_")
            else:
                prefix = ""
            if self.messages_prefix:
                prefix += "%010d" % self.events_in_this_file + "_"
            src = TEMP_DIRECTORY + self.filename
            shutil.copy(src, DEFAULT_DIRECTORY + prefix + self.filename) # os.rename() fails if they're on different drives
            os.remove(src)
            
            self.files_written.append(DEFAULT_DIRECTORY + self.filename)
            self.file = None
            self.filename = None
            self.first_timestamp = None
            self.file_count += 1

    def close(self):
        if len(self.last_event) != 0:
            self._write_event(self.last_event)
        self._close()

           
