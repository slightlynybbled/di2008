import coloredlogs
import logging
import ctypes

print('ctypes.WinDLL', ctypes.WinDLL('libusb-1.0.dll'))

import os
os.environ['PYUSB_DEBUG'] = 'debug'
# os.environ['PYUSB_LOG_FILENAME'] = 'C:\\_code\\di2008\\examples\\usblog.txt'

coloredlogs.install(level=logging.DEBUG)

import usb.core
import usb.util
import usb.backend.libusb1 as libusb1

devices = [d for d in usb.core.find(find_all=True,
                                    idVendor=0x0683,
                                    idProduct=0x2008)]

[print(d) for d in devices]

device = devices[0]
device.set_configuration()
