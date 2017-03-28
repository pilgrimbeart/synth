#!/usr/bin/env python

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

import json
import logging

import boto3

DEFAULT_TYPENAME = "DemoThingType"


class Api:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, aws_region=None):
        """Return a instance of the AWS API.
        
        The API will be configured from credentials in the environment/AWS Configure files, unless explicitly
        provided as arguments.
        
        See the following, for more information:
         * http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials
         * http://docs.aws.amazon.com/iot/latest/developerguide
        
        Args:
            aws_access_key_id (str, optional): AWS access key id
            aws_secret_access_key (str, optional): AWS access key secret
            aws_region (str, optional): AWS region to connect to.
            
        Returns:
            Api: Configured AWS API client.
        
        """
        if None not in (aws_access_key_id, aws_secret_access_key, aws_region):
            logging.info("Loading AWS iot/-data client with specific credentials")
            self.iotClient = boto3.client('iot',
                                          aws_access_key_id=aws_access_key_id,
                                          aws_secret_access_key=aws_secret_access_key,
                                          region_name=aws_region)
            self.iotData = boto3.client('iot-data',
                                        aws_access_key_id=aws_access_key_id,
                                        aws_secret_access_key=aws_secret_access_key,
                                        region_name=aws_region)
        else:
            logging.info("Loading AWS client with default credentials")
            self.iotClient = boto3.client('iot')
            self.iotData = boto3.client('iot-data')

    def create_device_type(self, type_name=DEFAULT_TYPENAME,
                           description="A Thing created by the DevicePilot Synth virtual device simulator"):
        """Creates a new type (lit. classification) of device.
        
        Args:
            type_name (str, optional):
                Name of the device type to be created.
                Creates a consistent synth default if not specified.
            description (str, optional): Description of the device type.
        Returns:
            str: AWS ARN of the thing type created (or already existing with that `type_name`).
        
        """
        logging.info("Creating AWS ThingType " + type_name)
        response = self.iotClient.create_thing_type(thingTypeName=type_name,
                                                    thingTypeProperties={'thingTypeDescription': description,
                                                                         'searchableAttributes': []})
        return response['thingTypeArn']

    def create_device(self, name, type_name=DEFAULT_TYPENAME):
        """Create a new device.
        
        Args:
            name (str): Name of the device to create.
            type_name (str, optional):
                Name of the device type to create a new device of (created if non-existant).
                Defaults to the consistent synth default type.
        Returns:
            str: AWS ARN of the created device (or already existing with that `name` and `type_name`).
            
        """
        logging.info("Creating AWS Thing " + name)
        self.create_device_type(type_name)
        response = self.iotClient.create_thing(thingName=name, thingTypeName=type_name)
        return response['thingArn']

    def get_device(self, name):
        """Gets the specified device.
        
        Args:
            name (str): Name of device to get.

        Returns:
            dict: JSON'esq dictionary of the specified device from AWS IoT.

        """
        response = self.iotData.get_thing_shadow(thingName=name)
        return response["payload"].read()

    def get_devices(self):
        """Returns a list of all IoT devices.
        
        Returns:
            dict: JSON'esq dictionary of all defined devices in AWS IoT.
        """
        return self.iotClient.list_things()['things']

    def post_device(self, device):
        """Posts the updated state of the specified device.
        
        Args:
            device (:obj:`Device`): Device to update. 
        
        Raises:
            AssertionError: Post failed.
            
        """
        self.post(device["$id"], device)

    def post(self, name, payload):
        """Post an update to the thing shadow of the named device.
        
        Args:
            name (str): Name of device to update shadow of.
            payload (dict): State of device to report.
        
        Raises:
            AssertionError: Post failed.
            
        """
        logging.info("Updating AWS device " + name + " : " + str(payload))
        data = {"state": {"reported": payload}}
        response = self.iotData.update_thing_shadow(thingName=name, payload=json.dumps(data))
        assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300

    def delete_device(self, name):
        """Deletes a device (and coresponding shadow, if created).
        
        Args:
            name (str): Name of device to delete.
        
        Returns:
            bool: True if delete was successful.
        
        """
        logging.info("Deleting AWS thing " + name + " (and its shadow if any)")

        try:
            response = self.iotData.delete_thing_shadow(thingName=name)
            assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300
            logging.info("(deleted shadow)")
        except AssertionError:
            logging.info("(no shadow to delete)")

        try:
            response = self.iotClient.delete_thing(thingName=name)
            assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300
            return True
        except AssertionError:
            logging.info("(no shadow to delete)")
            return False

    def delete_default_devices(self):
        """Deletes all devices with the synth consistent default type."""
        logging.info("Deleting AWS demo devices")
        for t in self.get_devices():
            if t['thingTypeName'] == DEFAULT_TYPENAME:
                self.delete_device(t['thingName'])
