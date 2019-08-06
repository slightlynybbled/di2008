Usage
=========

Hardware Setup
---------------

Place device into 'COM' mode:

 1. Disconnect from USB
 2. Wait 5 seconds
 3. Connect to USB and press button on side rapidly until LED changes

The device setting is persistent and will not need to be changed again.  In windows, you should see a COM port in your
device manager with the label `DATAQ DI-2008` when the device is in the appropriate mode.

Scanning Inputs
---------------

To read a few analog inputs, device setup is relatively simple.

 1. Define the ports
 2. Create the `Di2008` instance
 3. Add the scan list
 4. Start the scanning process
 5. Read inputs at whatever timing is desired as the inputs will be updated "live"

Some sample code might be more illuminating.  A simple script to set up the scan list and to print the values every
second::

    from time import sleep
    from di2008 import AnalogPort, RatePort, Di2008

    # create each of the inputs that need to be sampled
    an0 = AnalogPort(1, analog_range=10.0, filter='average')
    an1 = AnalogPort(2, thermocouple_type='j')
    an2 = AnalogPort(3, thermocouple_type='j')
    rate = RatePort(5000)

    daq = Di2008()
    daq.create_scan_list(
        [an0, an1, an2, rate]
    )
    daq.start()

    while True:
        print(f'{an0.value:.02f}')
        print(f'{an1.value:.02f}')
        print(f'{an2.value:.02f}')
        print(f'{rate.value:.02f}')
        print()

        sleep(1.0)

Writing to Digital Outputs
--------------------------

Writing to digital outputs is a two-stage process:

 1. Define the digital outputs as instances of ``DigitalPort``
 2. Setup the digital ports on the ``Di2008`` object
 3. Write the desired states to the digital ports

Sample code ::

    from time import sleep
    from di2008 import AnalogPort, RatePort, Di2008

    # create each of the inputs that need to be sampled
    d0 = DigitalPort(0, output=True)
    d2 = DigitalPort(2, output=True)

    daq = Di2008()
    daq.setup_digital(
        [d0, d2]
    )

    while True:
        daq.write_switch()
