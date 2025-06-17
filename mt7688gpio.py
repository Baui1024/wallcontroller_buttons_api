import asyncio
import os
import mmap
import struct


class MT7688GPIOAsync:
    BASE_ADDR = 0x10000000
    MAP_SIZE = 0x1000

    def __init__(self, pin: int):
        if os.geteuid() != 0:
            raise PermissionError("Run as root")

        self.full_pin = pin
        self.pin = pin if pin < 32 else pin - 32

        self.REG_DIR = 0x600 if pin < 32 else 0x604
        self.REG_POL = 0x610 if pin < 32 else 0x614
        self.REG_SET = 0x630 if pin < 32 else 0x634
        self.REG_CLR = 0x640 if pin < 32 else 0x644
        self.REG_DATA = 0x620 if pin < 32 else 0x624

        self.mem = open("/dev/mem", "r+b")
        self.map = mmap.mmap(self.mem.fileno(), self.MAP_SIZE, offset=self.BASE_ADDR)

        self._polling_task = None
        self._polling_cancel_event = asyncio.Event()

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

        pol = self._read(self.REG_POL)
        if flip:
            pol |= (1 << self.pin)
        else:
            pol &= ~(1 << self.pin)
        self._write(self.REG_POL, pol)

    def set_high(self):
        self._write(self.REG_SET, 1 << self.pin)

    def set_low(self):
        self._write(self.REG_CLR, 1 << self.pin)

    def read_input(self):
        return (self._read(self.REG_DATA) >> self.pin) & 1

    async def start_polling(self, callback, edge="rising", interval=0.01):
        self._polling_cancel_event.clear()
        last_state = self.read_input()

        async def poll_loop():
            nonlocal last_state
            while not self._polling_cancel_event.is_set():
                state = self.read_input()
                if (edge == "rising" and state == 1 and last_state == 0) or \
                   (edge == "falling" and state == 0 and last_state == 1) or \
                   (edge == "both" and state != last_state):
                    await callback(state, self.full_pin)
                last_state = state
                await asyncio.sleep(interval)

        self._polling_task = asyncio.create_task(poll_loop())

    async def stop_polling(self):
        self._polling_cancel_event.set()
        if self._polling_task:
            await self._polling_task

    def close(self):
        self.map.close()
        self.mem.close()





import time

async def on_change(state):
    print("Pin changed to:", state)

gpio = MT7688GPIOAsync(pin=16)
gpio.set_direction(is_output=False, flip=True)  # Set pin 16 as input

async def main():
    await gpio.start_polling(on_change, edge="both")
    await asyncio.sleep(10)
    await gpio.stop_polling()
    gpio.close()

asyncio.run(main())