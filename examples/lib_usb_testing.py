import logging
import os
from time import sleep

import usb.core
import usb.util
import usb.backend.libusb0 as libusb

logging.basicConfig(level=logging.DEBUG)
usb_logger = logging.getLogger('usb.core')
usb_logger.setLevel(logging.DEBUG)

# for p in os.environ.get('PATH').split(';'):
#     print(f'path: "{p}"')

backend = libusb.get_backend()
print('backend:', backend)
devices = [d for d in usb.core.find(find_all=True,
                                    idVendor=0x0683,
                                    idProduct=0x2008,
                                    backend=backend,
                                    )]

print(devices)
device = devices[0]
print(device)
print(type(device))
device.set_configuration(1)

# send "stop" command just in case the device happens to be scanning
device.write(0x1, 'stop')
sleep(0.2)

response = device.read(0x81, 64)
response = ''.join([chr(b) for b in response if b != 0])
print(f'response when nothing was sent: "{response}"')


def write(command: str):
    device.write(0x1, f'{command}\r\n')
    sleep(0.05)

    response = device.read(0x81, 64)
    response = ''.join([chr(b) for b in response if b != 0])

    sleep(0.05)
    return response.strip()

count = 0
max_count = 2
while count < max_count:
    for i in range(7):
        response = write(f'info {i}')
        print('response:', response)
        print([c for c in response])
    sleep(1)
    count += 1

