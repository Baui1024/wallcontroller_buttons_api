import websockets
import select
import threading
import json

class Button:
    def __init__(self, id: int, pin: int):
        self.socket = None
        self.id = id
        self.gpio_pin = pin
        self.gpio_address = f"/sys/class/gpio/gpio{pin}/value"
        self.gpio = None
        self.epoll = select.epoll()
        self.thread = threading.Thread(target=self.read_button, daemon=True)
        # self.thread.start()
    
    def setup_pin(self):
        # Set up GPIO pin for input
        try:
            with open("/sys/class/gpio/export", "w") as f:
                f.write(str(self.gpio_pin))
        except OSError:
            with open("/sys/class/gpio/unexport", "w") as f:
                f.write(f"{self.gpio_pin}")
            with open("/sys/class/gpio/export", "w") as f:
                f.write(str(self.gpio_pin))
        with open(f"/sys/class/gpio/gpio{self.gpio_pin}/direction", "w") as f:
            f.write("in")
        with open(f"/sys/class/gpio/gpio{self.gpio_pin}/edge", "w") as f:
            f.write("both")
        self.gpio = open(self.gpio_address, "r")
        self.epoll.register(self.gpio.fileno(), select.EPOLLIN | select.EPOLLET)
        print(f"Button {self.id} on GPIO pin {self.gpio_pin} set up for input")

    def read_button(self    ):
        try: 
            while True:
                events = self.epoll.poll()
                for fileno, event in events:
                    if fileno == self.gpio.fileno():
                        value = self.gpio.read().strip()
                        if value == '1':
                            print(f"Button {self.id} pressed")
                            cmd = {'command': 'button_press', 'button_id': self.id, 'value': int(value)}
                            if self.socket:
                                try: 
                                    print(f"Sending button press command for button {self.id}")
                                    self.socket.send(json.dumps(cmd))
                                except websockets.WebSocketConnectionClosedException:
                                    print(f"WebSocket connection closed while sending button press command for button {self.id}")
                        elif value == '0':
                            print(f"Button {self.id} released")
                            cmd = {'command': 'button_press', 'button_id': self.id, 'value': int(value)}
                            if self.socket:
                                try:    
                                    print(f"Sending button release command for button {self.id}")
                                    self.socket.send(json.dumps(cmd))
                                except websockets.WebSocketConnectionClosedException:
                                    print(f"WebSocket connection closed while sending button release command for button {self.id}")
        except Exception as e:
            raise RuntimeError(f"Error reading button {self.id} on GPIO pin {self.gpio_pin}: {e}")