import time
import asyncio
import threading
import gpiod
from gpiod.line import Direction, Value, Drive
from collections import namedtuple
from mt7688gpio import MT7688GPIO

Color = namedtuple('Color', ['r', 'g', 'b'])

class LED:
    def __init__(self, id: int, pin_r: int, pin_g: int, pin_b: int):
        self.pin_r = pin_r 
        self.pin_g = pin_g
        self.pin_b = pin_b
        self.color = Color(100, 0, 0) # LED is initially off
        self.state = True
        self.led = (PWMPin(id, pin_r), PWMPin(id, pin_g), PWMPin(id, pin_b))
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
    def __init__(self, id: int, pin: int):
        self.state = True
        self.gpio_pin = pin
        self.gpio_pin_register = MT7688GPIO(self.gpio_pin)
        self.gpio_pin_register.set_direction(is_output=True, flip=True)
        self.duty_cycle = 0.5  # Initial duty cycle is 50%
        self.frequency = 100  # Default max frequency in Hz
        self.high_time = 1/self.frequency * self.duty_cycle
        self.low_time = 1/self.frequency * (1 - self.duty_cycle)
        self.identify = False   
        self.counter = 0
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        

    def pin_on(self):
        self.gpio_pin_register.set_high()

    def pin_off(self):
        self.gpio_pin_register.set_low()

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
        try:
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
                        # print("on",time.time()-t)
                        
                    time.sleep(self.high_time)
                    self.pin_off()
                    # print("off",time.time()-t)
                    time.sleep(self.low_time)
                    # if self.gpio_pin == 14:
                    #     print(time.time())
        except Exception as e:
            self.gpio_pin_register.close()

if __name__ == "__main__":
    led = PWMPin(1,17)
    led.set_duty_cycle(0.1)
    led2 = PWMPin(1,21)
    led2.set_duty_cycle(0.1)
    

    time.sleep(15)

