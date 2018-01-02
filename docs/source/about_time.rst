Time
----
Time/date parameters are used throughout Synth. Here are some examples::

    "2017-01-01T00:00:00" # An ISO8601 format datetime. Note this is YYYY-MM-DDThh:mm:ss
    "PT5M"                # An ISO8601 duration *relative* to the current simulation time. So this means "5 minutes later".
    "now"                 # The current real time. For example, if you set engine `{ "start" : "now" }` then the simulation will start at the current real time. Or { "end" : "now" } will finish at the current time.
    "when_done"           # For end times, this means "when no further events are pending"
    null                  # For end times, this means "never"

Further examples of ISO8601 durations::

    * "PT0S"    # Immediately (no seconds later)
    * "PT5M"    # In 5 minutes
    * "P30D"    # In 30 days.
    * "-PT4H"   # 4 hours previously.

Note that *negative* durations are allowed in some contexts. For example if you set a simulation start time as "-PT4H" then the simulation will start 4 hours before now.

NOTE: Currently ISO8601 durations greater than Days are not correctly supported due to limitations of the <isodate> module. But it's fine to say e.g. "P360D" for a year.
