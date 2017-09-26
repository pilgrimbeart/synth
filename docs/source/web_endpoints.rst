Web endpoints
=============
Synth simulates not just device output, but also device input too. An external service can “prod” Synth to generate asynchronous events on devices, via its Web server, at scale. These events are synchronised via the simulation engine.

Some general URL queries allow the status of the Synth framework to be checked, and new simulations to be spawned. And a POST interface allows events to be sent to specific devices running in specific Synth instances.

A Flask web server handles incoming queries at HTTPS port 443 and sends them onto an internal ZeroMQ bus, from which they are consumed by a process spawner (to create new Synth instances) and, within each instance, an event listener to post events into its simulation engine.

.. automodule:: synth.web_to_zeromq