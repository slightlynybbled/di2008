import logging
from time import sleep

from di2008 import Di2008, DigitalDirection

logging.basicConfig(level=logging.DEBUG)

daq = Di2008()

daq.setup_dio_direction(0, DigitalDirection.OUTPUT)
daq.setup_dio_direction(1, DigitalDirection.OUTPUT)

while True:
    daq.write_do(0, False)
    daq.write_do(1, False)
    sleep(1.0)

    daq.write_do(0, True)
    daq.write_do(1, True)
    sleep(1.0)
