#!/usr/bin/env python
#
# A device-emulating client for AWS-IoT
#
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
#
# To understand AWS-IoT read: http://docs.aws.amazon.com/iot/latest/developerguide
# To understand the Boto library read: http://boto3.readthedocs.io
#
# Requirements:
#    pip install boto3
#    Log into the AWS web portal and create an access certificate
#    Install AWS CLI
#    Use "aws configure" to set up your certificate and region
#
# All devices created/deleted are of type DEFAULT_TYPENAME, so this library shouldn't affect existing devices

import logging, json
import boto3
from clients.client import Client

DEFAULT_TYPENAME = "DemoThingType"

class Aws(Client):
    def __init__(self, params):
        self.aws_access_key_id = params.get("aws_access_key_id", None)
        self.aws_secret_access_key = params.get("aws_secret_access_key", None)
        self.aws_region = params.get("aws_region", None)
        if self.aws_access_key_id != None:
            logging.info("Loading AWS iot client with specific credentials")
            self.iotClient = boto3.client('iot',
                                        aws_access_key_id=self.aws_access_key_id,
                                        aws_secret_access_key=self.aws_secret_access_key,
                                        region_name=self.aws_region)
            logging.info("Loading AWS iot-data client with specific credentials")
            self.iotData = boto3.client('iot-data',
                                        aws_access_key_id=self.aws_access_key_id,
                                        aws_secret_access_key=self.aws_secret_access_key,
                                        region_name=self.aws_region)
        else:   # Will pick up any credentials previously set using AWS Configure, or in environment variables http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials
            logging.info("Loading AWS client with default credentials")
            self.iotClient = boto3.client('iot')
            self.iotData = boto3.client('iot-data')

    def add_device(self, device_id, time, properties):
        """Add device, returning ARN. OK if thing already exists. Ignores <time>."""
        logging.info("Creating AWS Thing "+device_id)
        self.createDeviceType(DEFAULT_TYPENAME)  # Ensure type exists (inefficient!)
        response = self.iotClient.create_thing(thingName=device_id, thingTypeName=DEFAULT_TYPENAME)
        arn = response['thingArn']
        self.update_device(device_id, time, properties)
        return arn

    def update_device(self, device_id, time, properties):
        """Update device."""
        # topic = "$aws/things/"+name+"/shadow/update"
        # iotData.publish(topic=topic, qos=1, payload=properties)
        # Publish seems to return 200 OK regardless of whether it actually succeeds!
        # Ignores <time>
        logging.info("Updating AWS device "+device_id+" : "+str(properties))
        data = { "state" : { "reported" : properties } }
        response = self.iotData.update_thing_shadow(thingName=device_id,payload=json.dumps(data))
        assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300

    def enter_interactive(self):
        pass

    def tick(self):
        pass
    
    def close(self):
        pass

    def get_device(self, device_id):
        response = self.iotData.get_thing_shadow(thingName=device_id)
        return response["payload"].read()

    def get_devices(self):
        return self.iotClient.list_things()['things']

    def delete_device(self, device_id):
        logging.info("Deleting AWS thing "+device_id+" (and its shadow if any)")

        response = self.iotClient.delete_thing(thingName = device_id)
        assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300

        try:
            response = self.iotData.delete_thing_shadow(thingName=device_id)
            assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300
            logging.info("(deleted shadow)")
        except:
            logging.info("(no shadow to delete)")


    def deleteDemoDevices(self):
        logging.info("Deleting AWS demo devices")
        for t in self.getDevices():
            if t['thingTypeName'] == DEFAULT_TYPENAME:
                self.deleteDevice(t['thingName'])

    def createDeviceType(self,name=DEFAULT_TYPENAME,description="A Thing created by the DevicePilot Synth virtual device simulator"):
        """Create a new type of device and return its ARN. OK if thing type already exists."""
        logging.info("Creating AWS ThingType "+name)
        response = self.iotClient.create_thing_type(thingTypeName=name,
                                            thingTypeProperties={'thingTypeDescription' : description, 'searchableAttributes' : []})
        return response['thingTypeArn']

if __name__ == "__main__":
    logging.getLogger("").setLevel(logging.INFO)
    client = api()
##    if True:
##        deleteDemoDevices()
##        print "INITIALLY:\n",getDevices()
##        typeARN = createDeviceType()
##        thingARN = createDevice("MyFirstThing")
##        print "AFTER ADDING A DEMO DEVICE:\n",getDevices()
##    post("MyFirstThing", { "hello" : "world" })
##    result = get("MyFirstThing")
##    print result
