Time functions
==============
Time functions are functions which produce a value which varies over time, either continuously or discretely.

Implementational note: because Synth is event-driven, a time function may be asked for its state at any arbitrary moment in time. This makes implementation of some functions 'interesting'.

.. automodule:: synth.timefunctions.count
.. automodule:: synth.timefunctions.events
.. automodule:: synth.timefunctions.mix
.. automodule:: synth.timefunctions.propertydriven
.. automodule:: synth.timefunctions.pulsewave
.. automodule:: synth.timefunctions.randomwave
.. automodule:: synth.timefunctions.sinewave
