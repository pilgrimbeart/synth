Welcome to Synth
================

You need to build and test your Internet of Things services and applications before the "Things" themselves exist. You need to check they'll work at a greater scale than the number of devices currently in use. And it's hard to build effective regression tests using actual devices.

``Synth`` aims to solve these chicken-and-egg problems by generating realistic IoT test data, allowing you to test and scale your IoT services and applications ahead of device availability.

Synth can...
************
 * Simulate any number of devices
 * Simulate devices with various functions
 * Generate historical data, e.g. a full year of data
 * Generate live data for interactive or load-testing
 * Push data (historical or live) into IoT services such as AWS IoT and DevicePilot
 * Interactive test and demo your service
 * Generate output files in a variety of formats

Synth's plug-in architecture also makes it easy to modify and extend to suit your own needs.

Getting started
***************
To install Synth either::

	pip install git:github.com/devicepilot/synth

or::

	git clone https://github.com/devicepilot/synth

To check that Synth is installed correctly, do::

   python synth OnFStest full_fat_device

Initially this will fail because you need to create some directories as follows...

Directory structure
*******************
Synth uses various data directories, some of which are in the directory *above* the Synth source code because they contain sensitive data which we don't want to e.g. commit in git.
 * ``../synth_logs``: Synth creates output files here. You'll have to create this directory yourself the first time
 * ``../synth_accounts``: parameter files containing information about how to contact remote services such as IoT clients, and keys for them
 * ``../synth_certs``: keys for 3rd-party services used by some Synth modules (e.g. Google Maps)
 * ``scenarios``: parameter files defining different simulation scenarios - see below

Command-line arguments
**********************
Synth accepts any number of arbitrary command-line parameters::

	python synth {args}

Arguments are generally taken to be the names of corresponding JSON files in either the ``synth_accounts`` or ``scenarios`` directories. The convention (but it's only a convention) is to name account files ``On*`` and list them first.

So e.g.::

	python synth OnFStest full_fat_device

will make Synth run the ``scenarios/full_fat_device.json`` scenario on the account defined in ``../synth_accounts/OnFStest.json``.

Whilst accounts and scenarios are generally defined in parameter files as described below, it is also possible to make (or override) simple definitions by specifying JSON directly on the command line as an argument e.g.::

		python synth OnFStest full_fat_device {\"restart_log\" : true}

When Synth runs it emits various hopefully informative log messages. These are time-stamped with the current **simulation** time, which will not be the current real time (unless Synth has caught-up with real time).

Parameter Files
***************
Synth parameter files are JSON structures. To add self-documentation your Synth files you can use Python-style #comments, though as this is not standard JSON it's probably better practice to just add redundant comment parameters which Synth will ignore thus::

	{ "comment" : "this is a comment" }

Accounts
--------
These are stored in the ``..\synth_accounts`` directory and are personal to you. See bottom for examples - you'll need to edit these to include your own private keys etc.
An account file **must** contain:

 * "instance_name" : this defines what to call this running instance of Synth. It's used to name log files, and also to distinguish incoming event traffic intended for this particular instance
 * "client" {} : the name of the output client to use and any parameters it requires

Currently three types of Synth client are supported:

 * *filesystem*: A client which writes .csv files into the ../synth_logs directory. Because this doesn't access the Internet it functions offline and is good for experimenting with Synth.
 * *devicepilot*: A client which can write into a DevicePilot account using the /ingest endpoint. It can also delete devices and perform various other DevicePilot-specific functions such as setting-up filters, actions etc.. Note that large historical data is better bulk-uploaded by generating JSON files rather than 
 * *aws*: A client which can write into an AWS-IoT account

Clients are plug-ins, loaded by name, so you can add your own client just by defining its class in the synth/clients directory.

Scenarios
---------
These are stored in the ``scenarios`` directory. A set of examples is provided and you can change or copy these to suit your needs.

A scenario file **must** contain:

 * "engine" : {} : which simulation engine to use.
 * "events" : {} : events to generate during the simulation run.

Simulation Engines
------------------
Currently the only engine available is "sim" which requires just "start_time" and "end_time" to be defined e.g.::

    "engine" : {
        "type" : "sim",
        "start_time" : "now",
        "end_time" : "PT10S"
    }

You may also specify `end_after_events` to terminate the simulation after a precise number of events have been generated - helpful when constructing precise test scenarios - in which case you probably want to set `"end_time" : null`.

The `sim` engine is event-driven so it hops from event to event rather than ticking through e.g. milliseconds, so large time spans will simulate quickly if the events are sparse.

`sim` will never let the current simulation time advance past the current real time, because many IoT clients don't like having data from the future posted into them. So when it catches-up with real-time it prints a log message and then drops into real-time simulation, waiting second by second to ensure that it never advances past the current time. Thus `sim` is capable of creating an historical record and then seamlessly moving into real-time interactive simulation, which can be useful for constructing interactive service demos with a history.

A note about Time
-----------------
Time/date parameters in Synth are always strings and can be any of::

    "2017-01-01T00:00:00" # An ISO8601 format datetime
    "now"                 # The current real time. For example, if you set engine `{ "start" : "now" }` then the simulation will start at the current real time. Or { "end" : "now" } will finish at the current time.
    "PT5M"                # An ISO8601 duration, relative to the current simulation time. This for example means "5 minutes later". Negative durations are allowed in some contexts e.g. "-PT4H"
    null	              # For end times, this means "never"
    "when_done"           # For end times, this means "when no further events are pending"

NOTE: Currently ISO8601 durations greater than Days are not correctly supported due to a bug in the <isodate> module.

Events
------
The *events* section of a scenario file is a list of events to trigger during the simulation run. Each event requires at least::

    [
        "at" : "now"	# The time at which the event happens (can be relative)
        "action" : {}	# The action to conduct. Generally this create_device, but can also be a client-specific method
    ]

The event can optionally repeat, so for example a simulation which starts with the creation of 10 devices, one per minute, would look like this::

    "events" : [
        {
        "at" : "PT0S",
        "repeats" : 10,
        "interval" : "PT1M",
        "action": {
            "create_device" : {
                "functions" : {
                    ...
                }
            }
        }
    ]

Device Functions
****************
Devices are composed of **functions** which are plug-in defined in the **devices** directory. All devices inherit the Basic device function, which has a unique $id but doesn't actually do anything.
You can specify as many functions as you like. Functions are composable (a device is constructed by inheriting from all specified functions) so functions can interact with each other if necessary.
A list of currently-available functions and their parameters:

    * ???
    * ???
    * ???


Contribute!
***********
Synth is an open-source project released under the permissive MIT licence and you are very welcome to contribute to it at https://github.com/devicepilot/synth

Editing these docs
******************
This documentation is built using Sphinx. If you edit any documentation, run ``make html`` to regenerate this HTML documentation.


Example files
*************

Accounts
--------

``OnFStest.json``::

    {
        "instance_name" : "OnFStest",
        "web_key" : "dummy",
        "client" : {
            "type" : "filesystem",
            "filename" :"OnFStest"
        }
    }

Scenario files
--------------
[insert some here and document them]