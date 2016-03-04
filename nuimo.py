#!/usr/bin/env python

from bluepy.btle import UUID, DefaultDelegate, Peripheral, BTLEException
import itertools
import struct
import sys
import time
if sys.version_info >= (3, 0):
    from functools import reduce


class NuimoDelegate(DefaultDelegate):

    def __init__(self, nuimo):
        DefaultDelegate.__init__(self)
        self.nuimo = nuimo

    def handleNotification(self, cHandle, data):
        if int(cHandle) == self.nuimo.characteristicValueHandles['BATTERY']:
            print('BATTERY', ord(data[0]))
        elif int(cHandle) == self.nuimo.characteristicValueHandles['FLY']:
            print('FLY', ord(data[0]), ord(data[1]))
        elif int(cHandle) == self.nuimo.characteristicValueHandles['SWIPE']:
            print('SWIPE', ord(data[0]))
        elif int(cHandle) == self.nuimo.characteristicValueHandles['ROTATION']:
            value = ord(data[0]) + (ord(data[1]) << 8)
            if value >= 1 << 15:
                value = value - (1 << 16)
            print('ROTATION', value)
        elif int(cHandle) == self.nuimo.characteristicValueHandles['BUTTON']:
            print('BUTTON', ord(data[0]))


class NuimoDelegate3(DefaultDelegate):
    """ With Python v3, NuimoDelegate throws this exception:
Trying to connect to 78:CE:80:00:50:64. Press Ctrl+C to cancel.
Connected. Waiting for input events...
Traceback (most recent call last):
  File "/home/pi/nuimo.py", line 130, in <module>
    nuimo.waitForNotifications()
  File "/home/pi/nuimo.py", line 81, in waitForNotifications
    self.peripheral.waitForNotifications(1.0)
  File "/opt/hass/venv/lib/python3.4/site-packages/bluepy/btle.py", line 473, in waitForNotifications
    resp = self._getResp('ntfy', timeout)
  File "/opt/hass/venv/lib/python3.4/site-packages/bluepy/btle.py", line 343, in _getResp
    self.delegate.handleNotification(hnd, data)
  File "/home/pi/nuimo.py", line 31, in handleNotification
    print('BUTTON', ord(data[0]))
TypeError: ord() expected string of length 1, but int found

Also, bluepy needs to be patched to be Python v3 portable:
https://github.com/IanHarvey/bluepy/pull/112
    """

    def __init__(self, nuimo):
        DefaultDelegate.__init__(self)
        self.nuimo = nuimo

    def handleNotification(self, cHandle, data):
        if int(cHandle) == self.nuimo.characteristicValueHandles['BATTERY']:
            print('BATTERY', data[0])
        elif int(cHandle) == self.nuimo.characteristicValueHandles['FLY']:
            print('FLY', data[0], data[1])
        elif int(cHandle) == self.nuimo.characteristicValueHandles['SWIPE']:
            print('SWIPE', data[0])
        elif int(cHandle) == self.nuimo.characteristicValueHandles['ROTATION']:
            print('ROTATION not supported with Python v3')  # FIXME
        elif int(cHandle) == self.nuimo.characteristicValueHandles['BUTTON']:
            print('BUTTON', data[0])


class Nuimo:

    SERVICE_UUIDS = [
        UUID('0000180f-0000-1000-8000-00805f9b34fb'), # Battery
        UUID('f29b1525-cb19-40f3-be5c-7241ecb82fd2'), # Sensors
        UUID('f29b1523-cb19-40f3-be5c-7241ecb82fd1')  # LED Matrix
    ]

    CHARACTERISTIC_UUIDS = {
        UUID('00002a19-0000-1000-8000-00805f9b34fb') : 'BATTERY',
        UUID('f29b1529-cb19-40f3-be5c-7241ecb82fd2') : 'BUTTON',
        UUID('f29b1528-cb19-40f3-be5c-7241ecb82fd2') : 'ROTATION',
        UUID('f29b1527-cb19-40f3-be5c-7241ecb82fd2') : 'SWIPE',
        UUID('f29b1526-cb19-40f3-be5c-7241ecb82fd2') : 'FLY',
        UUID('f29b1524-cb19-40f3-be5c-7241ecb82fd1') : 'LED_MATRIX'
    }

    NOTIFICATION_CHARACTERISTIC_UUIDS = [
        #'BATTERY', # Uncomment only if you are not using the iOS emulator (iOS does't support battery updates without authentication)
        'BUTTON',
        'ROTATION',
        'SWIPE',
        'FLY']

    # Notification data
    NOTIFICATION_ON  = struct.pack("BB", 0x01, 0x00)
    NOTIFICATION_OFF = struct.pack("BB", 0x00, 0x00)

    def __init__(self, macAddress):
        self.macAddress = macAddress

    def set_delegate(self, delegate):
        self.delegate = delegate

    def connect(self):
        self.peripheral = Peripheral(self.macAddress, addrType='random')
        # Retrieve all characteristics from desires services and map them from their UUID
        characteristics = list(itertools.chain(*[self.peripheral.getServiceByUUID(uuid).getCharacteristics() for uuid in Nuimo.SERVICE_UUIDS]))
        characteristics = dict((c.uuid, c) for c in characteristics)
        # Store each characteristic's value handle for each characteristic name
        self.characteristicValueHandles = dict((name, characteristics[uuid].getHandle()) for uuid, name in Nuimo.CHARACTERISTIC_UUIDS.items())
        # Subscribe for notifications
        for name in Nuimo.NOTIFICATION_CHARACTERISTIC_UUIDS:
            self.peripheral.writeCharacteristic(self.characteristicValueHandles[name] + 1, Nuimo.NOTIFICATION_ON, True)
        self.peripheral.setDelegate(self.delegate)

    def waitForNotifications(self):
        self.peripheral.waitForNotifications(1.0)

    def displayLedMatrix(self, matrix, timeout, brightness = 1.0):
        matrix = '{:<81}'.format(matrix[:81])
        bytes = list(map(lambda leds: reduce(lambda acc, led: acc + (1 << led if leds[led] not in [' ', '0'] else 0), range(0, len(leds)), 0), [matrix[i:i+8] for i in range(0, len(matrix), 8)]))
        self.peripheral.writeCharacteristic(self.characteristicValueHandles['LED_MATRIX'], struct.pack('BBBBBBBBBBBBB', bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7], bytes[8], bytes[9], bytes[10], max(0, min(255, int(255.0 * brightness))), max(0, min(255, int(timeout * 10.0)))), True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python nuimo.py <Nuimo's MAC address>")
        sys.exit()

    nuimo = Nuimo(sys.argv[1])
    if sys.version_info >= (3, 0):
        nuimo.set_delegate(NuimoDelegate3(nuimo))
    else:
        nuimo.set_delegate(NuimoDelegate(nuimo))

    # Connect to Nuimo
    print("Trying to connect to %s. Press Ctrl+C to cancel." % sys.argv[1])
    try:
        nuimo.connect()
    except BTLEException:
        print("Failed to connect to %s. Make sure to:\n  1. Disable the Bluetooth device: hciconfig hci0 down\n  2. Enable the Bluetooth device: hciconfig hci0 up\n  3. Enable BLE: btmgmt le on\n  4. Pass the right MAC address: hcitool lescan | grep Nuimo" % nuimo.macAddress)
        sys.exit()
    print("Connected. Waiting for input events...")

    # Display some LEDs matrices and wait for notifications
    nuimo.displayLedMatrix(
        "         " +
        " ***     " +
        " *  * *  " +
        " *  *    " +
        " ***  *  " +
        " *    *  " +
        " *    *  " +
        " *    *  " +
        "         ", 2.0)
    time.sleep(2)
    nuimo.displayLedMatrix(
        " **   ** " +
        " * * * * " +
        "  *****  " +
        "  *   *  " +
        " * * * * " +
        " *  *  * " +
        " * * * * " +
        "  *   *  " +
        "   ***   ", 20.0)

    try:
        while True:
            nuimo.waitForNotifications()
    except BTLEException as e:
        print("Connection error:", e)
    except KeyboardInterrupt:
        print("Program aborted")
        """ FIXME: on Python 3, this exception is thrown:

Connected. Waiting for input events...
BUTTON 1
^CProgram aborted
Exception ignored in: <bound method Peripheral.__del__ of <bluepy.btle.Peripheral object at 0xb687d690>>
Traceback (most recent call last):
  File "/opt/hass/venv/lib/python3.4/site-packages/bluepy/btle.py", line 477, in __del__
  File "/opt/hass/venv/lib/python3.4/site-packages/bluepy/btle.py", line 375, in disconnect
  File "/opt/hass/venv/lib/python3.4/site-packages/bluepy/btle.py", line 232, in _writeCmd
BrokenPipeError: [Errno 32] Broken pipe """
