import boto3
import botocore
from botocore.config import Config
import sys
import time


current_time = str(int(time.time() * 1000))

records = [
    { "Dimensions" : [{"Name" : "$id", "Value" : "1", "DimensionValueType" : "VARCHAR"}], "MeasureName" : "temp", "MeasureValue" : "42.0", "MeasureValueType" : 'DOUBLE', "Time" : current_time },
    { "Dimensions" : [{"Name" : "$id", "Value" : "2", "DimensionValueType" : "VARCHAR"}], "MeasureName" : "temp", "MeasureValue" : "60.0", "MeasureValueType" : 'DOUBLE', "Time" : current_time },
]

try:
    result = write_client.write_records(DatabaseName=DATABASE_NAME, TableName=TABLE_NAME,
                                       Records=records, CommonAttributes={})
    print("WriteRecords Status: [%s]" % result['ResponseMetadata']['HTTPStatusCode'])
except write_client.exceptions.RejectedRecordsException as err:
    print("Some records were rejected")
except Exception as err:
    print("Error:", err)

print("Done")


class timestream_writer:
    def __init__(self, database_name, table_name):
        session = boto3.Session(profile_name="playground")
        write_client = session.client('timestream-write', config=Config(read_timeout=20, max_pool_connections = 5000, retries={'max_attempts': 10}))

        try:
            write_client.create_database(DatabaseName = database_name)
        except write_client.exceptions.ConflictException:
            print("Database already exists")
        except Exception as err:
            print("Can't create database", err)
        
        retention_properties = {
            'MemoryStoreRetentionPeriodInHours': 24,
            'MagneticStoreRetentionPeriodInDays': 7
        }
        try:
            write_client.create_table(DatabaseName = database_name, TableName = table_name, RetentionProperties=retention_properties)
        except write_client.exceptions.ConflictException:
            print("Table already exists")
        except Exception as err:
            print("Can't create table", err)

        self.write_client = write_client

    def write(data):
    """data expected to be an array of sets"""
    
    # ??? CHANGE THIS TO FILL ARRAY APPROPRIATELY
        records = [
            { "Dimensions" : [{"Name" : "$id", "Value" : "1", "DimensionValueType" : "VARCHAR"}], "MeasureName" : "temp", "MeasureValue" : "42.0", "MeasureValueType" : 'DOUBLE', "Time" : current_time },
            { "Dimensions" : [{"Name" : "$id", "Value" : "2", "DimensionValueType" : "VARCHAR"}], "MeasureName" : "temp", "MeasureValue" : "60.0", "MeasureValueType" : 'DOUBLE', "Time" : current_time },
        ]

        try:
            result = write_client.write_records(DatabaseName=DATABASE_NAME, TableName=TABLE_NAME,
                                            Records=records, CommonAttributes={})
            print("WriteRecords Status: [%s]" % result['ResponseMetadata']['HTTPStatusCode'])
        except write_client.exceptions.RejectedRecordsException as err:
            print("Some records were rejected")
        except Exception as err:
            print("Error:", err)


if __name__ == "__main__":
    writer = timestream_writer("FOO_DATABASE", "FOO_TABLE")
    T = time.time()
    writer.write([
        {"$id" : "1", "$ts" : T, "temp" : 42 },
        {"$id" : "2", "$ts" : T, "temp" : 60 }
    ])
]
 
