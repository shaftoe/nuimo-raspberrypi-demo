from bluepy.bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEException
import struct
import sys

# Characteristic UUIDs
BATTERY_VOLTAGE_CHARACTERISTIC    = "00002a19-0000-1000-8000-00805f9b34fb"
DEVICE_INFORMATION_CHARACTERISTIC = "00002a29-0000-1000-8000-00805f9b34fb"
LED_MATRIX_CHARACTERISTIC         = "f29b1523-cb19-40f3-be5c-7241ecb82fd1"
FLY_CHARACTERISTIC                = "f29b1526-cb19-40f3-be5c-7241ecb82fd2"
SWIPE_CHARACTERISTIC              = "f29b1527-cb19-40f3-be5c-7241ecb82fd2"
ROTATION_CHARACTERISTIC           = "f29b1528-cb19-40f3-be5c-7241ecb82fd2"
BUTTON_CLICK_CHARACTERISTIC       = "f29b1529-cb19-40f3-be5c-7241ecb82fd2"

# Notification handles
BATTERY_HANDLE  = 12
FLY_HANDLE      = 33
SWIPE_HANDLE    = 36
ROTATION_HANDLE = 39
CLICK_HANDLE    = 30

# Notification data
NOTIFICATION_ON  = struct.pack("BB", 0x01, 0x00)
NOTIFICATION_OFF = struct.pack("BB", 0x00, 0x00)

class NuimoDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        if int(cHandle) == BATTERY_HANDLE - 1:
            print "BATTERY", ord(data[0])
        elif int(cHandle) == FLY_HANDLE - 1:
            value = ord(data[0]) + ord(data[1]) << 8
            if value >= 1 << 15:
                value = value - 1 << 16
            print "FLY", value
        elif int(cHandle) == SWIPE_HANDLE - 1:
            print "SWIPE", ord(data[0])
        elif int(cHandle) == ROTATION_HANDLE - 1:
            value = ord(data[0]) + (ord(data[1]) << 8)
            if value >= 1 << 15:
                value = value - (1 << 16)
            print "ROTATION", value
        elif int(cHandle) == CLICK_HANDLE - 1:
            print "CLICK", ord(data[0])


class Nuimo:

    def __init__(self, macAddress='FA:48:12:00:CA:AC'):
        self.macAddress = macAddress

    def connect(self):
        self.peripheral = Peripheral(self.macAddress, addrType='random')
        self.peripheral.setDelegate(NuimoDelegate())
        self.enableNotifications()

    def enableNotifications(self):
        self.peripheral.writeCharacteristic(CLICK_HANDLE,    NOTIFICATION_ON)
        self.peripheral.writeCharacteristic(BATTERY_HANDLE,  NOTIFICATION_ON)
        self.peripheral.writeCharacteristic(FLY_HANDLE,      NOTIFICATION_ON)
        self.peripheral.writeCharacteristic(SWIPE_HANDLE,    NOTIFICATION_ON)
        self.peripheral.writeCharacteristic(ROTATION_HANDLE, NOTIFICATION_ON)

    def waitForNotifications(self):
        self.peripheral.waitForNotifications(1.0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: python nuimo.py <Nuimo's MAC address>"
        sys.exit()

    nuimo = Nuimo(sys.argv[1])

    print "Trying to connect to %s. Press Ctrl+C to cancel." % sys.argv[1]

    try:
        nuimo.connect()
    except BTLEException as e:
        print "Failed to connect to %s. Make sure to:\n  1. Enable the Bluetooth device: hciconfig hci0 up\n  2. Enable BLE: btmgmt le on\n  3. Pass the right MAC address: hcitool lescan | grep Nuimo" % nuimo.macAddress
        sys.exit()

    print "Connected. Waiting for input events..."

    try:
        while True:
            if nuimo.waitForNotifications():
                continue
    except BTLEException as e:
        print "Cannot connect to %s" % nuimo.macAddress, e.code
