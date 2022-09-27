import boto3
import botocore
from botocore.config import Config
import os, sys
import time
import logging
if __name__ == "__main__":
    from client import Client
else:
    from .client import Client
    from .client_helpers import client_workers


DEFAULT_NUM_WORKERS = 1

class Timestream(Client):
    def __init__(self, instance_name, context, params):
        logging.info("Initialising Timestream client with "+str(params))
        self.instance_name = instance_name
        self.context = context
        self.params = params
        if "setenv" in params:
            for (key, value) in params["setenv"].items():
                logging.info("SETENV "+key+" "+value)
                os.environ[key] = value

        if "profile_name" not in params:
            logging.warning("No profile specified for Timestream")

        session = boto3.Session(profile_name = params.get("profile_name", None))
        if session.get_credentials().secret_key:
            logging.info("Timestream sees an AWS secret key")
        else:
            logging.error("Timestream sees no AWS secret key")

        self.write_client = session.client('timestream-write', config=Config(read_timeout=20, max_pool_connections = 5000, retries={'max_attempts': 10}))

        try:
            self.write_client.create_database(DatabaseName = self.params["database_name"])
        except self.write_client.exceptions.ConflictException:
            logging.info("Database "+self.params["database_name"]+" already exists (this is OK)")
        
        retention_properties = {
            'MemoryStoreRetentionPeriodInHours': 24,
            'MagneticStoreRetentionPeriodInDays': 7
        }
        try:
            self.write_client.create_table(DatabaseName = params["database_name"], TableName = params["table_name"], RetentionProperties=retention_properties)
        except self.write_client.exceptions.ConflictException:
            logging.info("Table " + self.params["table_name"] + " already exists (this is OK)")

        self.num_workers = params.get("num_workers", DEFAULT_NUM_WORKERS)
        logging.info("Timestream module using "+str(self.num_workers)+" worker sub-processes to provide write bandwidth")

        explode_factor = params.get("explode_factor", 1)
        if explode_factor != 1:
            logging.info("Timestream explode factor set to "+str(explode_factor))

        self.workers = []
        for w in range(self.num_workers):
            self.workers.append(client_workers.WorkerParent(params))

    def add_device(self, device_id, time, properties):
        pass

    def update_device(self, device_id, time, properties):
        w = hash(properties["$id"]) % self.num_workers   # Shard onto workers by ID (so data from each device stays in sequence). Python hash is stable per run, not across runs.
        self.workers[w].enqueue(properties)

    def get_device(self, device_id):
        pass

    def get_devices(self):
        pass

    def delete_device(self, device_id):
        pass

    def enter_interactive(self):
        pass

    def tick(self, t):
        for w in self.workers:
            w.tick(t)

        client_workers.output_stats(self.workers)

    def async_command(self, argv):
        pass

    def close(self):
        for w in self.workers:
            w.wait_until_stopped()




if __name__ == "__main__":
    logging.root.setLevel(logging.INFO)
    writer = Timestream("instance_name", None, { "profile_name":"playground", "database_name":"FOO_DATABASE", "table_name":"FOO_TABLE"})
    writer._write([
        {"$id" : "1", "$ts" : time.time(), "temp" : 42 },
        {"$id" : "2", "$ts" : time.time(), "temp" : 60 }
    ])
 
