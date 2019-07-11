import logging
from time import sleep

from di2008 import Di2008, DigitalPort

logging.basicConfig(level=logging.DEBUG)

daq = Di2008(port_name='COM110', loglevel=logging.INFO)

d0 = DigitalPort(0, output=False)
d1 = DigitalPort(1, output=False)
d2 = DigitalPort(2, output=False)

daq.setup_digital([d0, d1, d2])

while True:
    print(f'D0: {d0.value}')
    print(f'D1: {d1.value}')
    print(f'D2: {d2.value}')
    print()

    sleep(1.0)
