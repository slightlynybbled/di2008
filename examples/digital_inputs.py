import logging
from time import sleep

from di2008 import Di2008, DigitalDirection

logging.basicConfig(level=logging.DEBUG)

daq = Di2008()

daq.setup_dio_direction(0, DigitalDirection.INPUT)
daq.setup_dio_direction(1, DigitalDirection.INPUT)
daq.setup_dio_direction(2, DigitalDirection.INPUT)

while True:
    print(f'D0: {daq.read_di(0)}')
    print(f'D1: {daq.read_di(1)}')
    print(f'D2: {daq.read_di(2)}')
    print()

    sleep(1.0)
