import time
import asyncio
import threading
import gpiod
from gpiod.line import Direction, Value
from collections import namedtuple
Color = namedtuple('Color', ['r', 'g', 'b'])

class LED:
    def __init__(self, pin_r: int, pin_g: int, pin_b: int):
        self.pin_r = pin_r 
        self.pin_g = pin_g
        self.pin_b = pin_b
        self.color = Color(255, 0, 0) # LED is initially off
        self.state = True
        self.led = (PWMPin(pin_r), PWMPin(pin_g), PWMPin(pin_b))
        self.update_pwm()

    def on(self):
        self.state = True
        self.update_pwm()

    def off(self):
        self.state = False
        self.update_pwm()

    def toggle(self):
        self.state = not self.state
        self.update_pwm()

    def set_color(self, color: Color):
        if not isinstance(color, Color):
            raise TypeError("Color must be an instance of Color namedtuple")
        self.color = color
        print(f"Setting LED color to R: {color.r}, G: {color.g}, B: {color.b}")
        self.update_pwm()
    
    def update_pwm(self):
        self.led[0].set_duty_cycle(self.color.r / 255)
        self.led[1].set_duty_cycle(self.color.g / 255)
        self.led[2].set_duty_cycle(self.color.b / 255)
        self.led[0].set_state(self.state)
        self.led[1].set_state(self.state)
        self.led[2].set_state(self.state)
        

class PWMPin:
    def __init__(self, pin):
        self.state = False
        self.gpio_pin = pin
        self.gpio_line = gpiod.request_lines("/dev/gpiochip0", {(self.gpio_pin) : gpiod.LineSettings(direction=Direction.OUTPUT)})
        self.duty_cycle = 0.5  # Initial duty cycle is 50%
        self.frequency = 50  # Default max frequency in Hz
        self.high_time = 1/self.frequency * self.duty_cycle
        self.low_time = 1/self.frequency * (1 - self.duty_cycle)
        self.identify = False   
        self.counter = 0
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        

    def pin_on(self):
        self.gpio_line.set_value(self.gpio_pin, Value.ACTIVE)

    def pin_off(self):
        self.gpio_line.set_value(self.gpio_pin, Value.INACTIVE)

    def identify_led(self, state: bool):
        self.identify = state

    def set_state(self, state: bool):
        self.state = state

    def set_duty_cycle(self, duty_cycle):
        if 0 <= duty_cycle <= 100:
            self.duty_cycle = duty_cycle
            self.high_time = 1/self.frequency * self.duty_cycle
            self.low_time = 1/self.frequency * (1 - self.duty_cycle)
            print(f"Set duty cycle of pin {self.gpio_pin} to {self.duty_cycle*100}%")
        else:
            raise ValueError("Duty cycle must be between 0 and 100")

    def run(self):
        t = time.time()
        while True:
            if self.identify:
                self.pin_off()
                print(f"Setting pin {self.gpio_path} LOW for identification")
                time.sleep(0.5)
                self.pin_on()
                print(f"Setting pin {self.gpio_path} HIGH for identification")
                time.sleep(0.5)
            else:
                if self.duty_cycle > 0 and self.state:
                    self.pin_on()
                time.sleep(self.high_time)
                self.pin_off()
                time.sleep(self.low_time)
                # if self.gpio_pin == 14:
                #     print(time.time())

if __name__ == "__main__":
    led = PWMPin(14)
    led.set_duty_cycle(0.1)
    led.frequency = 10

    time.sleep(15)

