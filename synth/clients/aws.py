#!/usr/bin/env python

# A devices-emulating client for AWS-IoT
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
    """AWS IoT API client for synth."""

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, aws_region=None):
        """Return an instance of the AWS API.
        
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
            self.iot_client = boto3.client('iot',
                                           aws_access_key_id=aws_access_key_id,
                                           aws_secret_access_key=aws_secret_access_key,
                                           region_name=aws_region)
            self.iot_data = boto3.client('iot-data',
                                         aws_access_key_id=aws_access_key_id,
                                         aws_secret_access_key=aws_secret_access_key,
                                         region_name=aws_region)
        else:
            logging.info("Loading AWS client with default credentials")
            self.iot_client = boto3.client('iot')
            self.iot_data = boto3.client('iot-data')

    def create_device_type(self, type_name=DEFAULT_TYPENAME,
                           description="A Thing created by the DevicePilot Synth virtual devices simulator"):
        """Creates a new type (lit. classification) of devices.
        
        Args:
            type_name (str, optional):
                Name of the devices type to be created.
                Creates a consistent synth default if not specified.
            description (str, optional): Description of the devices type.
        Returns:
            str: AWS ARN of the thing type created (or already existing with that `type_name`).
        
        """
        logging.info("Creating AWS ThingType " + type_name)
        response = self.iot_client.create_thing_type(thingTypeName=type_name,
                                                     thingTypeProperties={'thingTypeDescription': description,
                                                                          'searchableAttributes': []})
        return response['thingTypeArn']

    def create_device(self, name, type_name=DEFAULT_TYPENAME):
        """Create a new devices.
        
        Args:
            name (str): Name of the devices to create.
            type_name (str, optional):
                Name of the devices type to create a new devices of (created if non-existant).
                Defaults to the consistent synth default type.
                
        Returns:
            str: AWS ARN of the created devices (or already existing with that `name` and `type_name`).
            
        """
        logging.info("Creating AWS Thing " + name)
        self.create_device_type(type_name)
        response = self.iot_client.create_thing(thingName=name, thingTypeName=type_name)
        return response['thingArn']

    def get_device(self, name):
        """Gets the specified devices.
        
        Args:
            name (str): Name of devices to get.

        Returns:
            dict: JSON'esq dictionary of the specified devices from AWS IoT.

        """
        response = self.iot_data.get_thing_shadow(thingName=name)
        return response["payload"].read()

    def get_devices(self):
        """Returns a list of all IoT devices.
        
        Returns:
            dict: JSON'esq dictionary of all defined devices in AWS IoT.
        """
        return self.iot_client.list_things()['things']

    def post_device(self, device):
        """Posts the updated state of the specified devices.
        
        Args:
            device (:obj:`Device`): Device to update. 
        
        Raises:
            AssertionError: Post failed.
            
        """
        self.post(device["$id"], device)

    def post(self, name, payload):
        """Post an update to the thing shadow of the named devices.
        
        Args:
            name (str): Name of devices to update shadow of.
            payload (dict): State of devices to report.
        
        Raises:
            AssertionError: Post failed.
            
        """
        logging.info("Updating AWS devices " + name + " : " + str(payload))
        data = {"state": {"reported": payload}}
        response = self.iot_data.update_thing_shadow(thingName=name, payload=json.dumps(data))
        assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300

    def delete_device(self, name):
        """Deletes a devices (and coresponding shadow, if created).
        
        Args:
            name (str): Name of devices to delete.
        
        Returns:
            bool: True if delete was successful.
        
        """
        logging.info("Deleting AWS thing " + name + " (and its shadow if any)")

        try:
            response = self.iot_data.delete_thing_shadow(thingName=name)
            assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300
            logging.info("(deleted shadow)")
        except AssertionError:
            logging.info("(no shadow to delete)")

        try:
            response = self.iot_client.delete_thing(thingName=name)
            assert 200 <= int(response['ResponseMetadata']['HTTPStatusCode']) < 300
            return True
        except AssertionError:
            logging.info("(no shadow to delete)")
            return False

    def delete_default_devices(self):
        """Deletes all devices with the synth consistent default type."""
        logging.info("Deleting AWS demo devices")
        for thing in self.get_devices():
            if thing['thingTypeName'] == DEFAULT_TYPENAME:
                self.delete_device(thing['thingName'])
