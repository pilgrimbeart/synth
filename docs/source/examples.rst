Example files
*************

Accounts
--------
Accounts files are private files in ../synth_accounts and by convention start with "On...".
Here we have shown some typical structures of these files, but of course with the private key information replaced with "X"

`OnFStest.json`::

    {
        "instance_name" : "OnFStest",
        "web_key" : "dummy",
        "client" : {
            "type" : "filesystem",
            "filename" :"OnFStest"
        }
    }


`OnAWS.json`::

    {
        "instance_name" : "OnAWS",
        "web_key" : "XXXX",
        "aws_access_key_id" : "XXXXXXXXXXXXXXXXXXXX",
        "aws_secret_access_key" : "XXXXXX+XXXXXXXXXXXXXXXXXXXX/XXXXXXXXX+XXX",
        "aws_region" : "us-west-2"
    }

`OnDevicePilot.json`::

    {
        "instance_name" : "OnDevicePilot",
        "web_key" : "XXXXXXXXXXXXXXXX",
        "client" : {
            "type" : "devicepilot",
            "devicepilot_api" : "https://api.devicepilot.com",
            "devicepilot_key" : "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "queue_criterion" : "messages",
            "queue_limit" : 500
        }
    }


Scenario files
--------------
Please refer to the scenarios directory for examples of scenario files which are hopefully fairly self-explanatory, when read with the device function and time-function documentation here.
