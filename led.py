import time
import asyncio
import threading
# import gpiod
# from gpiod.line import Direction, Value, Drive
from collections import namedtuple
# from mt7688gpio import MT7688GPIOAsync

Color = namedtuple('Color', ['r', 'g', 'b'])

class LED:
    def __init__(self, id: int, pin_r: int, pin_g: int, pin_b: int):
        self.pin_r = pin_r 
        self.pin_g = pin_g
        self.pin_b = pin_b
        self.brightness = 1
        self.color = Color(0, 0, 0) # LED is initially off
        self.state = True
        # self.led = (PWMPin(pin_r), PWMPin(pin_g), PWMPin(pin_b))
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

    def set_brightness(self, brightness: int | float):
        brightness = float(brightness)
        if not (0.0 <= brightness <= 1.0):
            raise ValueError("Brightness must be between 0.0 and 1.0")

        self.brightness = brightness
        print(f"Setting LED brightness to {brightness}")
        self.update_pwm()
    

    def update_pwm(self):
        with open(f"/sys/class/leds/pca963x:led{self.pin_r}/brightness", 'w') as f:
            if self.state:
                f.write(str(int(self.color.r*self.brightness)))
            else:
                f.write("0")
        with open(f"/sys/class/leds/pca963x:led{self.pin_g}/brightness", 'w') as f:
            if self.state:
                f.write(str(int(self.color.g*self.brightness)))
            else:
                f.write("0")
        with open(f"/sys/class/leds/pca963x:led{self.pin_b}/brightness", 'w') as f:
            if self.state:
                f.write(str(int(self.color.b*self.brightness)))
            else:
                f.write("0")

if __name__ == "__main__":
    led = LED(1, 0, 1, 2)
    t = time.time()
    for x in range(255):
        led.set_color(Color(x, 255-x, 0))
        print(t-time.time())
    led.off()  # Turn off the LED
    # led = PWMPin(17)
    # led.set_duty_cycle(0.1)
    # led2 = PWMPin(1,21)
    # led2.set_duty_cycle(0.1)
    

