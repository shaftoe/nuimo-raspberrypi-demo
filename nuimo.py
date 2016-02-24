from bluepy.btle import DefaultDelegate, Peripheral, BTLEException
import struct
import sys
import time
if sys.version_info >= (3, 0):
    from functools import reduce

# Characteristic value handles
BATTERY_VALUE_HANDLE   = 11
FLY_VALUE_HANDLE       = 32
SWIPE_VALUE_HANDLE     = 35
ROTATION_VALUE_HANDLE  = 38
CLICK_VALUE_HANDLE     = 29
LEDMATRIX_VALUE_HANDLE = 26

# Notification handles
BATTERY_NOTIFICATION_HANDLE  = BATTERY_VALUE_HANDLE + 1
FLY_NOTIFICATION_HANDLE      = FLY_VALUE_HANDLE + 1
SWIPE_NOTIFICATION_HANDLE    = SWIPE_VALUE_HANDLE + 1
ROTATION_NOTIFICATION_HANDLE = ROTATION_VALUE_HANDLE + 1
CLICK_NOTIFICATION_HANDLE    = CLICK_VALUE_HANDLE + 1

# Notification data
NOTIFICATION_ON  = struct.pack("BB", 0x01, 0x00)
NOTIFICATION_OFF = struct.pack("BB", 0x00, 0x00)

class NuimoDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        if int(cHandle) == BATTERY_VALUE_HANDLE:
            print "BATTERY", ord(data[0])
        elif int(cHandle) == FLY_VALUE_HANDLE:
            value = ord(data[0]) + ord(data[1]) << 8
            if value >= 1 << 15:
                value = value - 1 << 16
            print "FLY", value
        elif int(cHandle) == SWIPE_VALUE_HANDLE:
            print "SWIPE", ord(data[0])
        elif int(cHandle) == ROTATION_VALUE_HANDLE:
            value = ord(data[0]) + (ord(data[1]) << 8)
            if value >= 1 << 15:
                value = value - (1 << 16)
            print "ROTATION", value
        elif int(cHandle) == CLICK_VALUE_HANDLE:
            print "CLICK", ord(data[0])


class Nuimo:

    def __init__(self, macAddress='FA:48:12:00:CA:AC'):
        self.macAddress = macAddress

    def connect(self):
        self.peripheral = Peripheral(self.macAddress, addrType='random')
        self.enableNotifications()
        self.peripheral.setDelegate(NuimoDelegate())

    def enableNotifications(self):
        self.peripheral.writeCharacteristic(CLICK_NOTIFICATION_HANDLE,    NOTIFICATION_ON)
        self.peripheral.writeCharacteristic(BATTERY_NOTIFICATION_HANDLE,  NOTIFICATION_ON)
        self.peripheral.writeCharacteristic(FLY_NOTIFICATION_HANDLE,      NOTIFICATION_ON)
        self.peripheral.writeCharacteristic(SWIPE_NOTIFICATION_HANDLE,    NOTIFICATION_ON)
        self.peripheral.writeCharacteristic(ROTATION_NOTIFICATION_HANDLE, NOTIFICATION_ON)

    def waitForNotifications(self):
        self.peripheral.waitForNotifications(1.0)

    def displayLedMatrix(self, matrix, timeout, brightness = 1.0):
        matrix = '{:<81}'.format(matrix[:81])
        bytes = list(map(lambda leds: reduce(lambda acc, led: acc + (1 << led if leds[led] not in [' ', '0'] else 0), range(0, len(leds)), 0), [matrix[i:i+8] for i in range(0, len(matrix), 8)]))
        self.peripheral.writeCharacteristic(LEDMATRIX_VALUE_HANDLE, struct.pack("BBBBBBBBBBBBB", bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7], bytes[8], bytes[9], bytes[10], max(0, min(255, int(255.0 * brightness))), max(0, min(255, int(timeout * 10.0)))))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: python nuimo.py <Nuimo's MAC address>"
        sys.exit()

    nuimo = Nuimo(sys.argv[1])

    # Connect to Nuimo
    print "Trying to connect to %s. Press Ctrl+C to cancel." % sys.argv[1]
    try:
        nuimo.connect()
    except BTLEException:
        print "Failed to connect to %s. Make sure to:\n  1. Enable the Bluetooth device: hciconfig hci0 up\n  2. Enable BLE: btmgmt le on\n  3. Pass the right MAC address: hcitool lescan | grep Nuimo" % nuimo.macAddress
        sys.exit()
    print "Connected. Waiting for input events..."

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
        print "Connection error:", e
    except KeyboardInterrupt:
        print "Program aborted"
