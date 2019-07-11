Classes
=============

Device
------------

The device is where all of the ports actually reside within.

.. autoclass:: di2008.Di2008
   :members:

Ports
-------------

Input ports are generally added into the scan list which the device scans in a round-robin method.  All inputs are
subclasses of the ``Port`` class.

.. autoclass:: di2008.AnalogPort
    :members:

.. autoclass:: di2008.DigitalPort
    :members:

.. autoclass:: di2008.RatePort
    :members:

.. autoclass:: di2008.CountPort
    :members:
