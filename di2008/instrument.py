"""
Implements some of the functionality of the DATAQ DI-2008 data acquisition module.
"""
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum
import logging
import threading
from time import sleep
from typing import List

import usb.backend.libusb0 as libusb0
import usb.core
import usb.util


_logger = logging.getLogger(__name__)

ENDPOINT_BULK_OUT = 0x1
ENDPOINT_BULK_IN = 0x81


def _discover_auto() -> 'usb.core.Device':
    available_devices = [d for d in usb.core.find(find_all=True,
                                                  idVendor=0x0683,
                                                  idProduct=0x2008,
                                                  backend=libusb0.get_backend())]
    if len(available_devices) == 0:
        raise AttributeError('there are no DI-2008 devices attached to the PC that are in USB mode')

    dev_strings = [str(d) for d in available_devices]
    _logger.debug(f'DI-2008 instruments detected on: {", ".join(dev_strings)}')

    device = available_devices[0]
    response = ''
    while 'stop' not in response:
        device.write(ENDPOINT_BULK_OUT, f'stop\r\n'.encode())
        sleep(0.05)

        response = device.read(ENDPOINT_BULK_IN, 64)
        response = ''.join([chr(b) for b in response if b != 0])
        response = response.strip()
        _logger.debug(f'stop command response: "{response}"')

    return device


def _discover_by_esn(serial_number: str) -> 'usb.core.Device':
    buffering_time = 0.05
    correct_device = None

    available_devices = [d for d in usb.core.find(find_all=True,
                                                  idVendor=0x0683,
                                                  idProduct=0x2008,
                                                  backend=libusb0.get_backend())]
    dev_strings = [str(d) for d in available_devices]
    _logger.debug(f'DI-2008 instruments detected on: {", ".join(dev_strings)}')

    for device in available_devices:
        _logger.info(f'checking candidate device "{device}"...')
        if correct_device is not None:
            break

        response = ''
        while 'stop' not in response:
            device.write(ENDPOINT_BULK_OUT, f'stop\r\n'.encode())
            sleep(buffering_time)
            response = device.read(ENDPOINT_BULK_IN, 128)
            response = ''.join([chr(b) for b in response if b != 0])
            response = response.strip()
            _logger.debug(f'stop command response: "{response}"')

        device.write(ENDPOINT_BULK_OUT, f'info 6\r\n'.encode('utf-8'))
        sleep(buffering_time)

        response = device.read(0x81, 128)
        response = ''.join([chr(b) for b in response if b != 0])
        response = response.strip()
        _logger.debug(f'message from {device}: "{response}"')

        parts = response.strip().split('\r\n')
        if len(parts) == 2:
            esn = parts[1].strip()
            if esn == serial_number.upper():
                correct_device = device

        if correct_device is not None:
            break

    if correct_device is None:
        raise AttributeError(f'DI-2008 serial number "{serial_number}" not found')
    else:
        _logger.info(f'DI-2008 serial number "{serial_number}" found on "{correct_device}"')

    return correct_device


class AnalogPortError(Exception):
    """
    Raised when there is an analog-port related error on the DI-2008
    """
    pass


class DigitalPortError(Exception):
    """
    Raised when there is a digital port related error on the DI-2008
    """
    pass


class PortNotValidError(Exception):
    """
    Raised when there is a port access attempted where a physical port does \
    not exist.
    """
    pass


class DigitalDirection(Enum):
    """
    Used to set the direction
    """

    INPUT = 0
    """Indicates that the port direction is to be an input"""

    OUTPUT = 1
    """Indicates that the port direction is to be an output"""


class Port:
    _mode_bit = 12
    _range_bit = 11
    _scale_bit = 8

    def __init__(self, callback: callable=None, loglevel=logging.DEBUG):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(loglevel)

        self._callback = callback

        self.value = None
        self._last_received = None
        self.configuration = 0
        self.commands = []

    @property
    def is_active(self):
        age = datetime.now() - self._last_received
        max_age = timedelta(seconds=3)

        if self._last_received is None or (age > max_age):
            self._logger.info(f'{self} does not appear to be active')
            self.value = None
            return False

        return True

    def parse(self, value):
        raise NotImplementedError


class AnalogPort(Port):
    """
    Analog input port which may be configured as a strict voltage monitor or \
    as a thermocouple input.

    :param channel: integer, the channel number as seen on the front of \
    the devices, which is to say, the first channel is ``1`` instead of ``0``
    :param analog_range: ``str`` or ``Decimal``, the expected range when configurated as an \
    analog input; valid values are in [`0.01`, `0.025`, `0.05`, `0.1`, `0.25`, `0.5`, \
    `1.0`, `2.5`, `5.0`, `10.0`, `25.0`, `50.0`] while invalid values will raise a \
    ``ValueError``
    :param thermocouple_type: string, a single letter denoting the \
    thermocouple type; valid values are in ['b', 'e', 'j', 'k', 'n', 'r', \
    's', 't'] and invalid values will raise a ``ValueError``
    :param filter: string, a string containing 'last point', 'average', \
    'maximum' or 'minimum' as defined in the device datasheet
    :param filter_decimation: int, an integer containing the number of \
    samples over which to filter as defined in the device datasheet
    :param loglevel: the logging level, i.e. ``logging.INFO``
    """
    def __init__(self, channel: int,
                 analog_range: (str, Decimal) = None, thermocouple_type: str = None,
                 filter: str = 'last point', filter_decimation: int = 10,
                 loglevel=logging.INFO):

        super().__init__(loglevel=loglevel)

        if channel == 0:
            raise AnalogPortError(f'channel 0 is invalid, note that the '
                                  f'channel numbers line up with the hardware.')

        if channel not in range(1, 9):
            raise AnalogPortError(f'channel "{channel}" is invalid, '
                                  f'expected 1 to 8, inclusivie')

        configuration = channel - 1

        self._logger.debug(f'starting configuration: {hex(configuration)}')

        if analog_range is not None and thermocouple_type is not None:
            raise ValueError(f'analog range and thermocouple type are '
                             f'both specified for analog channel {channel}')

        if analog_range is not None:
            if not isinstance(analog_range, Decimal):
                analog_range = Decimal(analog_range)

            valid_ranges = ['0.01', '0.025', '0.05', '0.1', '0.25', '0.5',
                            '1.0', '2.5', '5.0', '10.0', '25.0', '50.0']
            valid_ranges += [Decimal(r) for r in valid_ranges]
            if analog_range not in valid_ranges:
                strings = [str(v) for v in valid_ranges]
                raise ValueError('valid values for analog range: '
                                 f'{", ".join(strings)}')

            if analog_range >= Decimal('1.0'):
                configuration |= (1 << self._range_bit)  # set the range bit
                analog_range /= Decimal(100)  # change the range to make lookup easier
            self._logger.debug(f'configuration after range modifier: {hex(configuration)}')
            range_lookup = {
                Decimal('0.5'): 0, Decimal('0.25'): 1, Decimal('0.1'): 2,
                Decimal('0.05'): 3, Decimal('0.025'): 4, Decimal('0.01'): 5
            }

            configuration |= (range_lookup[analog_range] << self._scale_bit)
            self._logger.debug(f'configuration after analog range modifier: {hex(configuration)}')

        if thermocouple_type is not None:
            if thermocouple_type.lower() not in 'bejknrst':
                self._logger.warning(f'thermocouple type must be valid')
                return
            configuration |= 1 << self._mode_bit  # set the mode bit
            thermo_lookup = {
                'b': 0, 'e': 1, 'j': 2, 'k': 3, 'n': 4, 'r': 5, 's': 6, 't': 7
            }

            configuration |= (thermo_lookup[thermocouple_type.lower()]
                              << self._scale_bit)
            self._logger.debug(f'configuration after thermocouple type modifier: {hex(configuration)}')

        filter_types = ['last point', 'average', 'maximum', 'minimum']
        if filter.lower() not in filter_types:
            raise ValueError(f'the "filter" must be one of the following: '
                             f'{", ".join(filter_types)}')
        if filter_decimation < 1 or filter_decimation > 32767:
            raise ValueError('the "filter_decimation" parameter must be '
                             'between 1 and 32767, inclusive')

        filter_value = filter_types.index(filter.lower())

        self.configuration = configuration
        self._logger.info(f'final configuration: {hex(configuration)}')

        self.commands += [f'filter {channel-1} {filter_value}',
                          f'dec {filter_decimation}']

    @property
    def _is_tc(self):
        """
        Return 'True' if is a thermocouple, else 'False'
        """
        return (self.configuration & (1 << self._mode_bit)) > 0

    def __str__(self):
        channel = (self.configuration & 0xf) + 1

        string = f'analog input, channel {channel} '
        if self._is_tc:
            # string construction for thermocouple type
            string += 'thermocouple '

            tc_ranges = {
                0: 'B', 1: 'E', 2: 'J', 3: 'K', 4: 'N', 5: 'R', 6: 'S', 7: 'T'
            }
            tc_type = tc_ranges[(self.configuration &
                                 (0x7 << self._scale_bit)) >> self._scale_bit]

            string += f'type {tc_type}'

        else:
            string += 'range '

            ranges = [0.5, 0.25, 0.1, 0.05, 0.025, 0.01]
            range_bit = self.configuration & (1 << self._range_bit)
            if range_bit:
                ranges = [r * 100 for r in ranges]
            scale_factor = (self.configuration &
                            (0x7 << self._scale_bit)) >> self._scale_bit
            range_value = ranges[scale_factor]
            string += f'+/-{range_value}V'

        return string

    def parse(self, value):
        """
        The ``parse`` method is intended to be called by the Di2008 \
        class when it receives data associated with the ``AnalogPort``.

        :param value: 16-bit integer value representing the 'raw' data stream
        :return:
        """
        self._last_received = datetime.now()

        if self._is_tc:
            if value == 32767:
                self.value = None
                self._logger.warning('!!! thermocouple error, cannot '
                                     'communicate with sensor or the reading '
                                     'is outside the sensor\'s measurement '
                                     f'range on "{str(self)}"')
                return
            elif value == -32768:
                self.value = None
                self._logger.warning(f'!!! thermocouple error, thermocouple '
                                     f'open or not connected on "{str(self)}"')
                return

            # from datasheet...
            m_lookup = {
                'j': 0.021515, 'k': 0.023987, 't': 0.009155, 'b': 0.023956,
                'r': 0.02774, 's': 0.02774, 'e': 0.018311, 'n': 0.022888
            }
            b_lookup = {
                'j': 495, 'k': 586, 't': 100, 'b': 1035,
                'r': 859, 's': 859, 'e': 400, 'n': 550
            }

            tc_ranges = {
                0: 'b', 1: 'e', 2: 'j', 3: 'k', 4: 'n', 5: 'r', 6: 's', 7: 't'
            }
            tc_type = tc_ranges[(self.configuration &
                                 (0x7 << self._scale_bit)) >> self._scale_bit]

            m = m_lookup[tc_type]
            b = b_lookup[tc_type]

            self.value = value * m + b
            self._logger.debug(f'value "{value}" converted for '
                               f'"{str(self)}" is "{self.value:.2f}°C"')

            if self._callback:
                self._callback(self.value)

            return self.value

        ranges = [0.5, 0.25, 0.1, 0.05, 0.025, 0.01]
        range_bit = self.configuration & (1 << self._range_bit)
        if range_bit:
            ranges = [r * 100 for r in ranges]
        scale_factor = (self.configuration & (0x7 << self._scale_bit)) \
            >> self._scale_bit
        range_value = ranges[scale_factor]

        self.value = range_value * float(value) / 32768.0
        self._logger.debug(f'value "{value}" converted for '
                           f'"{str(self)}" is "{self.value:.5g}V"')

        if self._callback:
            self._callback(self.value)

        return self.value


class RatePort(Port):
    """
    Digital input port which may be configured as a frequency monitor.

    :param range_hz: the maximum range of the input, in Hz; valid values are \
    in [50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50, 20, 10] and \
    invalid values will raise a ``ValueError``
    :param filter_samples: filter samples as defined within the device \
    datasheet
    :param loglevel: the logging level, i.e. ``logging.INFO``
    """
    def __init__(self, range_hz: int = 50000, filter_samples: int = 32,
                 loglevel=logging.INFO):
        super().__init__(loglevel=loglevel)

        rates_lookup = {
            50000: 1, 20000: 2, 10000: 3, 5000: 4, 2000: 5, 1000: 6, 500: 7,
            200: 8, 100: 9, 50: 10, 20: 11, 10: 12
        }
        valid_rates = [r for r in rates_lookup.keys()]
        if range_hz not in valid_rates:
            raise ValueError(f'rate not valid, please choose a valid rate '
                             f'from the following: {", ".join(valid_rates)}')

        if not 1 <= filter_samples <= 64:
            raise ValueError(f'filter_samples not valid, must be '
                             f'between 1 and 64, inclusive')

        self.configuration = (rates_lookup[range_hz] << self._scale_bit) + 0x9
        self.commands += [f'ffl {filter_samples}']
        self._range = range_hz

    def __str__(self):
        return f'rate input, {self._range}Hz'

    def parse(self, value):
        self._last_received = datetime.now()

        self.value = self._range * (value + 32768) / 65536
        self._logger.debug(f'value "{value}" converted for '
                           f'"{str(self)}" is "{self.value:.4f}Hz"')

        if self._callback:
            self._callback(self.value)

        return self.value


class CountPort(Port):
    """
    todo: Implement and document CountPort
    """
    def __init__(self, loglevel=logging.DEBUG):
        super().__init__(loglevel=loglevel)

        self.configuration = 0xa
        raise NotImplementedError


class DigitalPort(Port):
    """
    A digital input/output port.

    :param channel: an integer corresponding to the digital channels as seen \
    on the front face of the device (zero-indexed)
    :param output: a boolean value, ``True`` if the channel is to be an output \
    else false.
    :param loglevel: the logging level to apply to the digital port.
    """
    def __init__(self, channel: int,
                 direction: DigitalDirection = DigitalDirection.INPUT,
                 loglevel=logging.INFO):
        super().__init__(loglevel=loglevel)

        if channel not in range(0, 7):
            raise DigitalPortError(f'channel "{channel}" '
                                   'is not a valid digital channel')

        self.channel = channel
        self.direction = direction
        self.value = False

    def __repr__(self):
        direction = 'output' \
            if self.direction == DigitalDirection.OUTPUT else 'input'
        return f'digital {direction} ' \
            f'{self.channel}'


class Di2008:
    """
    The device controller which implements its own ``threading.Thread`` class \
    and processes incomming data based on its defined scan list.  The
    ``port_name`` and ``serial_number`` allow the user to specify a
    particular device on the bus when there may be more than one device
    present on the bus.  If both ``port_name`` and ``serial_number`` are
    specified, then ``serial_number`` will take precedence.  If neither
    are specified, then the first instrument found on the bus will be
    automatically acquired.

    :param port_name: the COM port (if not specified, the software will \
    attempt to find the device)
    :param serial_number: the serial number of the device to acquire
    :param timeout: the period of time over which input data is pulled from \
    the serial port and processed
    :param loglevel: the logging level, i.e. ``logging.INFO``
    """
    def __init__(self, serial_number: str = None, timeout=0.05, loglevel=logging.INFO):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(loglevel)

        self._timeout = timeout
        self._scanning = False
        self._scan_index = 0
        self._device = None
        self._ports = []
        self._dio = [DigitalPort(x) for x in range(0, 7)]
        self._raw = []

        self._manufacturer = None
        self._pid = None
        self._firmware = None
        self._esn = None

        # initialize the command queue with basic information requests
        self._command_queue = [
            'stop', 'info 0', 'info 1', 'info 2', 'info 6', 'srate 4'
        ]

        success = self._discover(serial_number)

        if success:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def __str__(self):
        return f'{self._manufacturer} DI-{self._pid}, serial number ' \
            f'{self._esn}, firmware {self._firmware}'

    @property
    def is_scanning(self):
        return self._scanning

    def change_led_color(self, color: 'str'):
        """
        Change the LED color.

        :param color: the color as a string; valid values are in \
        ['black', 'blue', 'green', 'cyan', 'red', 'magenta', 'yellow', \
        'white'] and invalid values will raise a ``ValueError``
        :return: None
        """
        colors_lookup = {
            'black': 0, 'blue': 1, 'green': 2, 'cyan': 3,
            'red': 4, 'magenta': 5, 'yellow': 6, 'white': 7
        }
        valid_colors = [c for c in colors_lookup.keys()]

        if color.lower() not in valid_colors:
            raise ValueError(f'color not valid, should be one of '
                             f'{", ".join(valid_colors)}')

        self._command_queue.append(f'led {colors_lookup[color.lower()]}')

    def setup_dio_direction(self, channel: int, direction: DigitalDirection):
        """
        Setup the digital port direction for a single port.

        :param channel: the channel number
        :param direction: the ``DigitalDirection``
        :return: None
        """
        if channel not in range(0, 7):
            raise PortNotValidError('the specified port/channel '
                                    f'"{channel}" does not exist')

        self._logger.info(f'setting digital channel {channel} to {direction}')

        directions = 0x00

        # load the directions from the current dio
        for i, port in enumerate(self._dio):
            value = 1 if port.direction == DigitalDirection.OUTPUT else 0
            directions |= value << i

        # modify the direction for the appropriate channel
        if direction == DigitalDirection.OUTPUT:
            directions |= 1 << channel
        else:
            directions &= ~(1 << channel)

        self._dio[channel].direction = direction

        self._command_queue.append(f'endo {directions}')

    def write_do(self, channel: int, state: bool):
        """
        Writes to any of the digital pins in the switch state.

        :param channel: an integer indicating the digital output
        :param state: the value, ``True`` or ``False``; ``True`` releases the \
        internal switch, meaning that the output will float up to 5V while \
        ``False`` will activate the internal switch, pulling the node to 0V
        :return: None
        """
        if channel not in range(0, 7):
            raise PortNotValidError('the specified port/channel '
                                    f'"{channel}" does not exist')

        self._logger.info(f'setting digital channel {channel} to {state}')

        values = 0x00
        for i, dio in enumerate(self._dio):
            if dio.direction == DigitalDirection.OUTPUT:
                if channel == i:
                    state_value = 0 if state else 1
                    values |= state_value << i
                    dio.value = state
                else:
                    state_value = 0 if dio.value else 1
                    values |= state_value << i

        self._command_queue.append(f'dout {values}')

    def read_di(self, channel: int):
        """
        Reads the state of any digital input/output

        :param channel: the channel number as shown on the instrument
        :return: True if the channel is high, else False
        """
        if channel not in range(0, 7):
            raise PortNotValidError('the specified port/channel '
                                    f'"{channel}" does not exist')

        return self._dio[channel].value

    def create_scan_list(self, scan_list: List[Port]):
        """
        Builds the scan list.  This must be done while the instrument is not \
        currently scanning or results are unpredictable.

        :param scan_list: a list of ``Port`` types.
        :return: True if success, else False
        """
        # create a scan list based on the provided list
        for port in scan_list:
            if not isinstance(port, Port):
                raise ValueError(f'"{port}" is not an instance of Port class')

        if len(scan_list) > 11:
            raise ValueError('scan list may only be a maximum '
                             'of 11 elements long')

        # todo: check for duplicates and raise ValueError if duplicate detected

        self._ports = scan_list

        # change the packet size based on the scan list length
        if len(scan_list) < 8:
            packet_size_id = 0
        elif len(scan_list) < 16:
            packet_size_id = 1
        elif len(scan_list) < 32:
            packet_size_id = 2
        else:
            packet_size_id = 3
        self._command_queue.append(f'ps {packet_size_id}')

        # create the scan list
        commands = [f'slist {offset} {port.configuration}' for offset, port in enumerate(self._ports)]

        # add any other port-specific commands
        for port in self._ports:
            for command in port.commands:
                commands.append(command)

        commands.append('info 9')

        # shift the entire command list into the transmit queue
        [self._command_queue.append(c) for c in commands]

        return True

    def start(self):
        """
        Starts the device scanning.  The scan list must already be defined \
        using ``create_scan_list`` method.

        :return: None
        """
        self._command_queue.append('start')

    def stop(self):
        """
        Stops the device scanning.
        :return:
        """
        for p in self._ports:
            p.value = None
        self._scanning = False

        self._send_cmd('stop')
        _logger.warning('asynchronous stop, device scanning halted')

        # give a couple of extra timeout
        # intervals for instrument to catch up
        sleep(self._timeout*2)

        for p in self._ports:
            p.value = None

    def close(self):
        """
        Release the device and serial port.

        :return: None
        """
        self._logger.warning('depreciated - close is not valid when using '
                             'the USB mode and is left here for compatibility')

    def _recover_buffer_overflow(self):
        self._command_queue = []
        self.stop()
        self.create_scan_list(self._ports)
        self.start()

    def _discover(self, serial_number: str = None):
        if serial_number is not None:
            self._device = _discover_by_esn(serial_number)
        else:
            self._device = _discover_auto()

        self._logger.info(f'device found on {self._device}')

        if self._device is not None:
            return True

        raise ValueError('DI-2008 not found on bus')

    def _send_cmd(self, command: str):
        self._logger.debug(f'sending "{command}"')
        try:
            self._device.write(ENDPOINT_BULK_OUT, f'{command}\r\n'.encode())
        except KeyError as e:
            self._logger.error(f'unknown exception during USB write event: {e}')

    def _parse_received(self, received):
        if self._scanning:
            values = [int(c) for c in received]
            self._logger.debug(f'received {len(values)}B from unit (scanning): {values}')

            self._raw += values
            while len(self._raw) > 1:
                low_byte = self._raw.pop(0)
                high_byte = self._raw.pop(0)
                int_value = low_byte + high_byte * 256
                if int_value > 32767:
                    int_value = int_value - 65536

                self._logger.debug(f'idx {self._scan_index} received: low={low_byte} high={high_byte} int={int_value}')
                self._ports[self._scan_index].parse(int_value)
                self._scan_index += 1
                self._scan_index %= len(self._ports)

        else:
            self._logger.debug(f'received from unit: {repr(received)}')
            received = ''.join([chr(b) for b in received if b != 0])

            if 'info' in received:
                self._parse_info(received)

            elif 'din' in received:
                self._parse_din(received)

            elif 'stop' in received:
                self._scanning = False

            elif 'ps' in received:
                if '0' in received:
                    packet_size = 16
                elif '1' in received:
                    packet_size = 32
                elif '2' in received:
                    packet_size = 64
                elif '3' in received:
                    packet_size = 128
                else:
                    packet_size = None
                self._logger.info(f'packet size set to is {packet_size} bytes')

            else:
                self._logger.info(f'message could not be parsed: {repr(received)}')

    def _parse_info(self, message):
        if 'info' not in message:
            return

        # make numbers to data
        if 'info 0' in message:
            self._manufacturer = message.split('info 0')[-1].strip()
            if self._manufacturer != 'DATAQ':
                self.close()

        elif 'info 1' in message:
            self._pid = message.split('info 1')[-1].strip()
            if self._pid != '2008':
                self.close()

        elif 'info 2' in message:
            self._firmware = message.split('info 2')[-1].strip()

        elif 'info 6' in message:
            self._esn = message.split('info 6')[-1].strip()

        else:
            self._logger.warning(f'info message not understood: {repr(message)}')

    def _parse_din(self, message):
        try:
            number = int(message.split(' ')[-1].strip())
        except ValueError as e:
            _logger.error(f'error processing "din" message: {repr(message)}')
            return

        for i, port in enumerate(self._dio):
            if port.direction == DigitalDirection.INPUT:
                if (number & (1 << i)) > 0:
                    port.value = True
                else:
                    port.value = False

            self._logger.debug(f'digital {port} is {port.value}')

    def _maintain_send_queue(self):
        if len(self._command_queue) > 0:
            command = self._command_queue.pop(0)
            self._logger.debug(f'processing command queue, next command: "{command}"')

            if 'start' in command:
                self._scanning = True
                self._scan_index = 0

            # collect the dout commands and only send the most recent
            if 'dout' in command:
                dout_indexes = []
                for i, cmd in enumerate(self._command_queue):
                    if 'dout' in cmd:
                        dout_indexes.append(i)

                if len(dout_indexes) == 0:
                    self._send_cmd(command)
                    return

                command = self._command_queue[dout_indexes[-1]]
                self._command_queue = [c for c in self._command_queue
                                       if 'dout' not in c]
                self._send_cmd(command)

            else:
                self._send_cmd(command)

        else:
            # when there is nothing else to do, poll the digital inputs...
            self._command_queue.append('din')

    def _run(self):
        timeout_ms = int(self._timeout*1000)
        while self._device:

            # read all messages waiting in the queue
            while True:
                try:
                    response = self._device.read(ENDPOINT_BULK_IN, 64, timeout=timeout_ms)
                    self._parse_received(response)
                except (usb.core.USBTimeoutError, usb.core.USBError):
                    break
                except Exception as e:
                    self._logger.warning(f'unknown error: {e}')
                    break

            self._maintain_send_queue()

            sleep(self._timeout)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print(_discover_by_esn('5C76AEFA'))
    print(_discover_auto())
