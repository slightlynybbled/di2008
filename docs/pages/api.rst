API
=============

Exceptions
------------

.. autoclass:: di2008.AnalogPortError

----

.. autoclass:: di2008.DigitalPortError

----

.. autoclass:: di2008.PortNotValidError

Device
------------

The device is where all of the ports actually reside within.

.. autoclass:: di2008.Di2008
  :members:

Ports
-------------

Input ports are generally added into the scan list which the device scans in a
round-robin method.  All inputs are subclasses of the ``Port`` class.

.. autoclass:: di2008.DigitalDirection
    :members:

----

.. autoclass:: di2008.AnalogPort
    :members:
    :inherited-members:

----

.. autoclass:: di2008.DigitalPort
    :members:
    :inherited-members:

----

.. autoclass:: di2008.RatePort
    :members:
    :inherited-members:

----

.. autoclass:: di2008.CountPort
    :members:
    :inherited-members:
