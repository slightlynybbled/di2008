from di2008.instrument import AnalogPort, RatePort, CountPort, DigitalPort, \
    Di2008, AnalogPortError, DigitalPortError, PortNotValidError, \
    DigitalDirection
from di2008.version import __version__

import os
os.environ['PYUSB_DEBUG'] = 'debug'

__all__ = ['AnalogPort', 'RatePort', 'CountPort', 'DigitalPort', 'Di2008',
           'AnalogPortError', 'DigitalPortError', 'PortNotValidError',
           'DigitalDirection',
           '__version__']
