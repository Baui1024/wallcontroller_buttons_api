#!/usr/bin/env python3
import os
import mmap
import struct
import time

class MT7688GPIO:
    BASE_ADDR = 0x10000000
    MAP_SIZE = 0x1000


    def __init__(self, pin: int):
        if os.geteuid() != 0:
            raise PermissionError("Run as root")

        self.REG_DIR   = 0x600 if pin < 32 else 0x604  # Direction register
        self.REG_POL   = 0x610 if pin < 32 else 0x614  # Polarity register
        self.REG_SET   = 0x630 if pin < 32 else 0x634  # Set bits
        self.REG_CLR   = 0x640 if pin < 32 else 0x644  # Clear bits
        self.REG_DATA  = 0x620 if pin < 32 else 0x624  # Read current input level
        self.pin = pin if pin < 32 else pin - 32
        self.mem = open("/dev/mem", "r+b")
        self.map = mmap.mmap(self.mem.fileno(), self.MAP_SIZE, offset=self.BASE_ADDR)

    def _read(self, offset):
        self.map.seek(offset)
        return struct.unpack("<I", self.map.read(4))[0]

    def _write(self, offset, value):
        self.map.seek(offset)
        self.map.write(struct.pack("<I", value))

    def set_direction(self, is_output, flip=False):
        val = self._read(self.REG_DIR)
        if is_output:
            val |= (1 << self.pin)
        else:
            val &= ~(1 << self.pin)
        self._write(self.REG_DIR, val)
        if flip:
            self._write(self.REG_POL, 1 << self.pin)
        else:
            self._write(self.REG_POL, 0 << self.pin)


    def set_high(self):
        self._write(self.REG_SET, 1 << self.pin)

    def set_low(self):
        self._write(self.REG_CLR, 1 << self.pin)

    def read_input(self):
        return (self._read(self.REG_DATA) >> self.pin) & 1

    def close(self):
        self.map.close()
        self.mem.close()


if __name__ == "__main__":
    pin = 37  # e.g. GPIO24
    gpio = MT7688GPIO(pin)



    gpio.set_direction(is_output=True, flip=True)
    t = time.time()
    for x in range(5000):
        if x % 2 == 0:
            gpio.set_low()
        else:
            gpio.set_high()
        print(time.time() - t)
        t = time.time()
    gpio.set_high()
    time.sleep(1)  # Keep the pin high for 1 second
    gpio.set_low()  # Set the pin low
    # wait or toggle
    # gpio.set_low(pin)

    gpio.close()
