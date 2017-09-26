Output file formats
===================
Synth produces output files in the `../synth_logs` directory in several different formats:

.json files
-----------
JSON files are arrays of events. Each event is a set of `property:value` pairs. Each event must contain a $id property identifying the device, and a $ts containing the timestamp (as epoch-milliseconds). Other properties are optional.

For example::

    [
    {"$id": "6a-02-d2-4c-5d-31", "$ts": 1483228800000, "is_demo_device": true, "label": "Thing 0"},
    {"$id": "6a-02-d2-4c-5d-31", "$ts": 1483232340000},
    {"$id": "1f-6e-8f-2c-8d-5a", "$ts": 1483232400000, "is_demo_device": true, "label": "Thing 1"},
    {"$id": "6a-02-d2-4c-5d-31", "$ts": 1483235880000},
    ...
    ]

In the above a first device 6a..31 defines two properties `is_demo_device` and `label`. 59 minutes later that device has a heartbeat (with no other properties sent).  Then a second device is created with similar properties, then the first device has another heartbeat.
Because $id and $ts are both keys, it is legal to have the same $ts value occur on multiple lines with different $id values (if properties on multiple devices change simultaneously).

This format happens to be DevicePilot's "bulk history loading" format.

.evt files
----------
Like JSON files, event files are minimalist event-based files, but with lined-oriented. The same simulation run as above would create the following .evt output::

    *** New simulation starting at real time Tue Sep 26 14:10:18 2017 (local)
    2017-01-01 00:00:00 $id,"6a-02-d2-4c-5d-31",$ts,1483228800.0,is_demo_device,true,label,"Thing 0",
    2017-01-01 00:59:00 $id,"6a-02-d2-4c-5d-31",$ts,1483232340.0,
    2017-01-01 01:00:00 $id,"1f-6e-8f-2c-8d-5a",$ts,1483232400.0,is_demo_device,true,label,"Thing 1",
    2017-01-01 01:58:00 $id,"6a-02-d2-4c-5d-31",$ts,1483235880.0,
    ...

The first 20 characters of each line is a datetime (matching the $ts field), followed by "property_name, property_value" pairs.
Note that a final trailing comma on each line is allowed.
Comment lines begin with `***`

.csv files
----------

These are Microsoft Excel "comma-separated value" files. Unlike the above file formats, every column must be specified on every row. However if values haven't changed, then the cell can be empty. The first row is a header row. $ts is in epoch-seconds::
    $ts,$id,battery,is_demo_device,label
    1483228800.0,6a-02-d2-4c-5d-31,100,True,Thing 0,
    1483232340.0,6a-02-d2-4c-5d-31,,,,
    1483232400.0,1f-6e-8f-2c-8d-5a,100,True,Thing 1,
    1483235880.0,6a-02-d2-4c-5d-31,,,,

