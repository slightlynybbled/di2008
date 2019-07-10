import logging
from time import sleep

from di2008 import Di2008, AnalogPort, RatePort

logging.basicConfig(level=logging.DEBUG)

daq = Di2008(port_name='COM110', loglevel=logging.INFO)

an1 = AnalogPort(1, analog_range=10.0, filter='average')
an2 = AnalogPort(2, thermocouple_type='j')
an3 = AnalogPort(3, thermocouple_type='j')
rate = RatePort(5000)

daq.create_scan_list(
    [an1, an2, an3, rate]
)
daq.start()

# wait for values to to start coming in
while not all([an1.value, an2.value, an3.value]):
    sleep(0.1)

while True:
    print(f'CH1 analog value: {an1.value:.02f}')
    print(f'CH2 temperature: {an2.value:.02f}')
    print(f'CH3 temperature: {an3.value:.02f}')
    print(f'Rate counter: {rate.value:.02f}')
    print()

    sleep(1.0)
