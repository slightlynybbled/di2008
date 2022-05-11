import coloredlogs
import logging
from time import sleep

from di2008 import Di2008, AnalogPort, RatePort

loglevel = logging.INFO
coloredlogs.install(level=loglevel)

daq = Di2008(loglevel=loglevel)

channels = [
    RatePort(5000),
    AnalogPort(1, analog_range=10.0, filter='average', loglevel=loglevel),
    AnalogPort(2, analog_range=10.0, loglevel=loglevel),
    AnalogPort(3, analog_range=10.0, loglevel=loglevel),
    AnalogPort(8, analog_range=10.0, loglevel=loglevel),
]

daq.create_scan_list(channels)
daq.start()


# wait for values to start coming in...
while not all([1 if ch.value is not None else 0
               for ch in channels]):
    sleep(0.1)

print('initialized.....')
count = 0
while count < 20:
    print([f'{ch.value:.5g}' for ch in channels])

    sleep(1)
    count += 1

daq.stop()
count = 0
max_count = 2
while count < max_count:
    print('count:', max_count-count)
    sleep(0.2)
    count += 1
