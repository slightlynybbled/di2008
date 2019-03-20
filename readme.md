# Purpose

To provide an easy-to-use, object-oriented instrument interface for the [DATAQ DI-2008](https://www.dataq.com/products/di-2008/) from within any Python environment.

The intent of this project is not to provide an API that will be useful in 100% of use cases, but will target the 90%.  In my experience, most of us need pretty basic functionality and have only modest timing requirements when working with such instrumentation.  As a result of this, the API will attempt to abstract away the lowest-level functionality which may result in a hiding or loss of feature implementation available in the hardware.  If this happens to you, feel free to use the nuts and bolts exposed herein to inform your own development or, better yet, send us a pull request!

# Installation

The hardware drivers must be installed before this package may be utilized.  Hardware drivers may be downloaded from the [manufacturer's product page](https://www.dataq.com/products/di-2008/).

Once drivers are installed:

    $> pip install di2008

# Project Status and Future

The objects provided are tested and demonstrated to function well, however, there are still lots of features that have not been implemented.

Items marked out have already been completed.  The list is in approximate order of priority and marked out items have been completed.

 * ~~Implement Analog Scan List~~ complete
 * ~~Read Thermocouples~~ complete
 * ~~Read Analog Inputs~~ complete
 * ~~Read Rate Input~~ complete
 * Read Event Input
 * Read Counter Input
 * Read Digital Input(s)
 * Write to Digital Outputs
 * Better sample hardware timing control
 * Hardware Synchronization

# Usage

Regarding the specifics of usage, it may be very helpful for the user to read the device documentation so that some of the concepts enshrined herein are more precisely interpreted.  Specifically, the concept of a "scan list" is somewhat unique to the product and difficult to abstract.  As the project matures, more of the hardware idiosyncrasies are expected to be exposed to the user.

## Hardware Setup

Place device into 'COM' mode:

 1. Disconnect from USB
 2. Wait 5 seconds
 3. Connect to USB and press button on side rapidly until LED changes
 
The device setting is persistent and will not need to be changed again.  You should see a COM port in your device manager with the label `DATAQ DI-2008` when the device is in the appropriate mode.

## Software Setup

To read a few analog inputs, device setup is relatively simple.

 1. Define the ports
 2. Create the `Di2008` instance
 3. Add the scan list
 4. Start the scanning process
 5. Read inputs at whatever timing is desired as the inputs will be updated "live"

Some sample code might be more illuminating.  A simple script to set up the scan list and to print the values every second:

    from time import sleep
    from di2008 import AnalogPort, RatePort, Di2008
    
    # create each of the inputs that need to be sampled
    an0 = AnalogPort(0, analog_range=10.0, filter='average')
    an1 = AnalogPort(1, thermocouple_type='j')
    an2 = AnalogPort(2, thermocouple_type='j')
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
        
# Contributions

Project could use some work, particularly in documentation.
