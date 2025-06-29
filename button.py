import websockets
import select
import threading
import gpiod
import asyncio
from gpiod.line import Edge
from mt7688gpio import MT7688GPIOAsync

import json
import time

class Buttons:
    def __init__(self, pins: dict[int, int]):
        self.socket = None
        self.pins = pins
        self.gpios = []
        self.states = [0] * len(pins)  # Initialize states for each button
        # self.open_gpio()
        # self.thread = threading.Thread(target=self.watch_multiple_line_values, daemon=True)
        # self.thread.start()
    
    async def open_gpio(self):
        self.line_offsets = tuple(self.pins.values())
        self.button_ids = tuple(self.pins.keys())
        for offset in self.line_offsets:
            gpio = MT7688GPIOAsync(offset)
            gpio.set_direction(is_output=False, flip=True)
            await gpio.start_polling(self.on_change, edge="both")

    async def close_gpio(self):
        for gpio in self.gpios:
            await gpio.stop_polling()
            gpio.close()
        self.gpios.clear()

    async def on_change(self, state, pin):
        for offset in self.line_offsets:
            if pin == offset:
                cmd = {}
                if state == 1 and self.states[self.line_offsets.index(pin)] == 0:
                    print("Rising edge detected on line {}".format(pin))
                    self.states[self.line_offsets.index(pin)] = 1
                    cmd = {'command': 'button_press', 'button_id': self.button_ids[self.line_offsets.index(pin)], 'value': 1}
                elif state == 0 and self.states[self.line_offsets.index(pin)] == 1:
                    self.states[self.line_offsets.index(pin)] = 0
                    print("Falling edge detected on line {}".format(pin))
                    cmd = {'command': 'button_press', 'button_id': self.button_ids[self.line_offsets.index(pin)], 'value': 0}
                if self.socket and cmd != {}:
                    try:
                        print(f"Sending button press command for button {self.button_ids[self.line_offsets.index(pin)]}")
                        await self.socket.send(json.dumps(cmd))
                    except websockets.ConnectionClosed:
                        print(f"WebSocket connection closed while sending button press command for button {self.button_ids[self.line_offsets.index(pin)]}")

    
    # async def watch_multiple_line_values(self):
    #     try:
    #         while True:
    #             events = await asyncio.to_thread(self.gpio.read_edge_events)
    #             for event in events: #request.read_edge_events():
    #                 cmd = {}
    #                 if event.event_type is event.Type.RISING_EDGE:
    #                     print("Rising edge detected on line {}".format(event.line_offset))
    #                     cmd = {'command': 'button_press', 'button_id': self.button_ids[self.line_offsets.index(event.line_offset)], 'value': 0}
    #                 if event.event_type is event.Type.FALLING_EDGE:
    #                     print("Falling edge detected on line {}".format(event.line_offset))
    #                     cmd = {'command': 'button_press', 'button_id': self.button_ids[self.line_offsets.index(event.line_offset)], 'value': 1}
    #             # time.sleep(0.01)  # Polling interval
    #                 if self.socket:
    #                     try: 
    #                         print(f"Sending button press command for button {self.button_ids[self.line_offsets.index(event.line_offset)]}")
    #                         await self.socket.send(json.dumps(cmd))
    #                     except websockets.ConnectionClosed:
    #                         print(f"WebSocket connection closed while sending button press command for button {self.button_ids[self.line_offsets.index(event.line_offset)]}")
    #     except OSError as ex:
    #         print(ex, "\nCustomise the example configuration to suit your situation")

if __name__ == "__main__":
    # Example usage
    button_pins = {1: 25,}  # Example GPIO pins for buttons
    buttons = Buttons(button_pins)
    time.sleep(10)  # Keep the main thread alive to allow button monitoring



#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2023 Kent Gibson <warthog618@gmail.com>

# """Minimal example of watching for edges on multiple lines."""
# import time
# import gpiod

# from gpiod.line import Edge


# def edge_type_str(event):
#     if event.event_type is event.Type.RISING_EDGE:
#         return "Rising"
#     if event.event_type is event.Type.FALLING_EDGE:
#         return "Falling"
#     return "Unknown"


# def watch_multiple_line_values(chip_path, line_offsets):
#     with gpiod.request_lines(
#         chip_path,
#         consumer="watch-multiple-line-values",
#         config={tuple(line_offsets): gpiod.LineSettings(edge_detection=Edge.BOTH)},
#     ) as request:
#         while True:
#             print(time.time(),"loop")
#             for event in request.read_edge_events():
                
#                 print(
#                     "offset: {}  type: {:<7}  event #{}  line event #{}".format(
#                         event.line_offset,
#                         edge_type_str(event),
#                         event.global_seqno,
#                         event.line_seqno,
#                     )
#                 )


# if __name__ == "__main__":
#     try:
#         watch_multiple_line_values("/dev/gpiochip0", [23,])
#     except OSError as ex:
#         print(ex, "\nCustomise the example configuration to suit your situation")