Welcome to Synth
================

Connected devices are being deployed in every market sector in increasing numbers. A significant challenge of the Internet of Things is how to test IoT services? Services must typically be brought-up ahead of the widespread availability of the devices they will serve, yet testing a service requires an estate of devices to test it with – a chicken-and-egg problem. And as a proposition grows in the market, operators will wish to continually test services at a scale perhaps an order-of-magnitude greater than the number of devices currently in use, to find bottlenecks and weaknesses in the service.

    * Manually testing a service with physical devices is far too slow and error-prone and simply doesn’t fit within a modern CI/CD/TDD framework
    * Maintaining an estate of physical devices for automated testing has some merits – but is impractical at a scale of more than 100 or so devices, and doesn’t scale well across many developers
    * Therefore there is a need for a tool capable of synthesising virtual devices, at scale. Such emulated devices then comprise a virtual device ‘estate’ which can be thrown at a service to prove that it works correctly at any scale

Synth is such a tool. It has the unusual capability to create data both in batch and interactive modes, and seamlessly to morph from one to the other, making it useful for several purposes including: 

    * Generating realistic device datasets: both static and historical time-series
    * Dynamic testing of services
    * Demonstrating IoT services interactively, having first generated a plausible history to this moment, without requiring access to real user data which is often subject to data confidentiality.

Synth's plug-in architecture also makes it easy to modify and extend to suit your own needs. Synth was developed as a tool to help test and demonstrate DevicePilot, the cloud service for managing IoT devices, but it’s independent of DevicePilot and can be used with any framework - it comes with an AWS-IoT client too, for example. 

Synth was released under the permissive open-source MIT license in 2017. 

Getting started
***************
To see what Python version you have installed type::

    python -V

Synth requires Python 2.7.x so if you're on some other Python version then we recommend using `venv` to create a Python 2.7 environment into which to install Synth.

To install Synth type::

	git clone https://github.com/devicepilot/synth

then::

    pip install -r requirements.txt

To test that Synth is installed correctly:

1) Create an account file `../synth_accounts/OnFStest.json` containing::

    {
        "instance_name" : "OnFStest",
        "client" :
        {
            "type" : "filesystem",
            "filename" :"OnFStest"
        }
    }

2) Ensure there's a scenario file in `scenarios/10secs` containing::

    {
        "device_count" : 10,
        "start_time" : "now",
        "end_time" : "PT10S",
        "install_timespan" : 10
    }

3) Now on the command line, from the top-level Synth directory (i.e. the one which contains the README file) run::

    python synth OnFStest 10secs

This will run for 10 seconds and create output files including::

    ../synth_logs/OnFStest.evt  - a log of all generated events
    ../synth_logs/OnFStest.csv  - the output from the 'filesystem' client

Directory structure
*******************
Synth uses various data directories, some of which are in the directory *above* the Synth source code because they contain sensitive data which we don't want to e.g. commit in git.
 * ``scenarios``: parameter files defining different simulation scenarios - see below
 * ``../synth_accounts``: parameter files containing information about how to contact remote services such as IoT clients, and keys for them
 * ``../synth_logs``: Synth creates output files here


Command-line arguments
**********************
Synth accepts any number of arbitrary command-line parameters::

	python synth {args}

Arguments are generally taken to be the names of corresponding JSON files in either the ``synth_accounts`` or ``scenarios`` directories. The convention (but it's only a convention) is to name account files ``On*`` and list them first::

	python synth OnFStest full_fat_device

will make Synth run the ``scenarios/full_fat_device.json`` scenario on the account defined in ``../synth_accounts/OnFStest.json``.

Synth also loads the file ``../synth_accounts/default.json`` at startup, if it exists, and this is where you can put universal parameters such as your Google Maps API key.

Whilst accounts and scenarios are generally defined in parameter files as described below, it is also possible to make (or override) simple definitions by specifying JSON directly on the command line as an argument e.g.::

		python synth OnFStest full_fat_device {\"restart_log\" : true}

When Synth runs it emits various hopefully informative log messages. These are time-stamped with the current **simulation** time, which will not be the current real time (unless Synth has caught-up with real time).

Parameter Files
***************
Synth parameter files are JSON structures. To add self-documentation your Synth files you can add comments using C, Javascript or Python syntax, though as this is not standard JSON it's probably better practice to just add redundant comment parameters which Synth will ignore, thus::

	{ "comment" : "this is a comment" }

Accounts
--------
These are stored in the ``..\synth_accounts`` directory and are personal to you. See bottom for examples - you'll need to edit these to include your own private keys etc.
An account file **must** contain:

 * "instance_name" : this defines what to call this running instance of Synth. It's used to name log files, and also to distinguish incoming event traffic intended for this particular instance
 * "client" {} : the name of the output client to use and any parameters it requires

Certificates
************
The ../synth_accounts directory may also contain ``ssl.crt`` and ``ssl.key`` files the two SSL certificate files necessary to enable Flask to securely accept and make HTTPS:// connections (so you only need these files if you're using inbound web events e.g. from DevicePilot)

Clients
-------
Clients take synth output and send it into some IoT system to simulate devices. Several Synth :doc:`clients` are supported. Clients are plug-ins, loaded by name, so you can add your own client just by defining its class in the synth/clients directory.

Scenarios
---------
These are stored in the ``scenarios`` directory. A set of examples is provided and you can change or copy these to suit your needs.

A scenario file **must** contain:

 * "engine" : {} : which simulation client engine to use
 * "events" : {} : events to generate during the simulation run

Simulation Engines
------------------
Simulation engines are the heart of Synth. Currently the only engine available is "sim" which requires just "start_time" and "end_time" to be defined e.g.::

    "engine" : {
        "type" : "sim",
        "start_time" : "now",
        "end_time" : "PT10S"
    }

You may also specify `end_after_events` to terminate the simulation after a precise number of events have been generated - helpful when constructing precise test scenarios - in which case you probably want to set `"end_time" : null`.

The `sim` engine is event-driven so it hops from event to event rather than ticking through e.g. milliseconds, so large time spans will simulate quickly if the events are sparse.

`sim` will never let the current simulation time advance past the current real time, because many IoT clients don't like having data from the future posted into them. So when it catches-up with real-time it prints a log message and then drops into real-time simulation, waiting second by second to ensure that it never advances past the current time. Thus `sim` is capable of creating an historical record and then seamlessly moving into real-time interactive simulation, which can be useful for constructing interactive service demos with a history.

What next
*********
Have a look at some scenario files and once you're ready to try modifying and creating them, the following references will be useful:

    * :doc:`about_time`
    * :doc:`clients`
    * :doc:`events_and_actions`
    * :doc:`device_functions`
    * :doc:`time_functions`

Contribute!
***********
Synth is an open-source project released under the permissive MIT licence. We welcome your contributions and feature requests at https://github.com/devicepilot/synth

Copyright (c) 2017 DevicePilot Ltd.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Editing these docs
******************
This documentation is built using Sphinx. If you edit any documentation, run ``make html`` to regenerate this HTML documentation.
