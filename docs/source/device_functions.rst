Device functions
================

Devices are composed of **functions** (each of which is a Python plug-in located in the **synth/devices** directory. All devices inherit the Basic device function. You can specify as many functions for a device as you like. Functions are composable (a device is constructed by inheriting from all specified functions) so functions can interact with each other if necessary.

Each function optionally takes some parameters (typically specified in a scenario .json file) and optionally creates and manages some device properties.

.. automodule:: synth.devices.basic
.. automodule:: synth.devices.battery
.. automodule:: synth.devices.button
.. automodule:: synth.devices.comms
.. automodule:: synth.devices.commswave
.. automodule:: synth.devices.enumerated
.. automodule:: synth.devices.expect
.. automodule:: synth.devices.firmware
.. automodule:: synth.devices.heartbeat
.. automodule:: synth.devices.latlong
.. automodule:: synth.devices.light
.. automodule:: synth.devices.names
.. automodule:: synth.devices.variable
