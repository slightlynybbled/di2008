import logging
from time import sleep

from di2008 import Di2008, DigitalPort

logging.basicConfig(level=logging.DEBUG)

daq = Di2008(port_name='COM110', loglevel=logging.INFO)

d0 = DigitalPort(0, output=True)
d1 = DigitalPort(1, output=True)
d2 = DigitalPort(2, output=True)
d3 = DigitalPort(3, output=True)
d4 = DigitalPort(4, output=True)
d5 = DigitalPort(5, output=True)
d6 = DigitalPort(6, output=True)

switches = [d0, d1, d2, d3, d4, d5, d6]

daq.setup_digital(switches)

while True:
    [d.pull_down() for d in switches]
    daq.write_switch(switches)
    sleep(1.0)

    [d.release() for d in switches]
    daq.write_switch(switches)
    sleep(1.0)
