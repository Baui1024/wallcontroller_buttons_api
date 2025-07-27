import asyncio
import ssl
import websockets
from led import LED, Color
from button import Buttons
import json
import logging 
import os
from mt7688gpio import MT7688GPIOAsync


# Ensure log directory exists
os.makedirs('logs', exist_ok=True)

logger = logging.getLogger(__name__)

#logging.basicConfig(filename='logs/example.log', encoding='utf-8', level=logging.DEBUG)
                    #!/bin/sh

PORT = 8765
CERT_FILE = "/etc/ssl/certs/wallcontroller.crt"
KEY_FILE = "/etc/ssl/private/wallcontroller.key"


LEDs = (
    LED(id = 2, pin_r=14, pin_g=13, pin_b=12),  #rb flipped in current revision
    LED(id = 4, pin_r=0, pin_g=1, pin_b=2),    
    LED(id = 3, pin_r=10, pin_g=9, pin_b=8),    #rgb flipped in current revision
    LED(id = 1, pin_r=4, pin_g=5, pin_b=6),  
)

gpio = MT7688GPIOAsync(pin=19)
gpio.set_direction(is_output=True, flip=True)  # Set pin 19 as output//OE for PCA9635
gpio.set_high()  # Set OE pin high to enable output

input_buttons = Buttons({
    1: 18,  # Button ID 2 on GPIO pin 28
    2: 15,  # Button ID 3 on GPIO pin 16
    3: 16,  # Button ID 4 on GPIO pin 20
    4: 17,  # Button ID 1 on GPIO pin 24
})



# Create the SSL context
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

# Client handler
async def handle_connection(websocket):
    remote_address = websocket.remote_address[0]
    logger.info(f"[+] Secure connection from {remote_address}")
    input_buttons.socket = websocket  # Assign the WebSocket to the buttons for sending commands
    await input_buttons.open_gpio()
    try:
        async for message in websocket:
            logger.debug(f"[>] {message}")
            try:
                data = json.loads(message)
                if 'command' in data:
                    command = data['command']
                    led_index = data.get('led_index', [])  # Convert to zero-based index
                    if command == 'set_color':
                        color = data.get('color', "#000000")
                        hex_color = color.lstrip('#')
                        r = int(hex_color[0:2], 16)
                        g = int(hex_color[2:4], 16)
                        b = int(hex_color[4:6], 16)
                        color_obj = Color(r, g, b)
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].set_color(color_obj)
                                await websocket.send(json.dumps({"succes": f"LED {index + 1} color set to {color}"}))
                            else:
                                await websocket.send(json.dumps({"error": "Invalid LED index"}))
                    elif command == 'set_brightness':
                        brightness = data.get('brightness', 1.0)
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].set_brightness(brightness)
                                await websocket.send(json.dumps({"succes": f"LED {index + 1} brightness set to {brightness}"}))
                            else:
                                await websocket.send(json.dumps({"error": "Invalid LED index"}))
                    elif command == 'toggle':
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].toggle()
                                await websocket.send(json.dumps({"succes": f"LED {index + 1} toggled"}))
                        else:
                            await websocket.send(json.dumps({"error": "Invalid LED index"}))
                    elif command == 'on':
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].on()
                                await websocket.send(json.dumps({"succes": f"LED {index + 1} turned ON"}))
                        else:
                            await websocket.send(json.dumps({"error": "Invalid LED index"}))
                    elif command == 'off':
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].off()
                                await websocket.send(json.dumps({"succes": f"LED {index + 1} turned OFF"}))
                        else:
                            await websocket.send(json.dumps({"error": "Invalid LED index"}))
                    else:
                        await websocket.send(json.dumps({"error": "Unknown command"}))
                else:
                    await websocket.send("No command provided")
            except json.JSONDecodeError:
                await websocket.send('{"error": "Invalid JSON format"}')
    except websockets.ConnectionClosed:
        logger.info(f"[-] Connection closed from {remote_address}")
        input_buttons.socket = None
        await input_buttons.close_gpio()

# Main event loop
async def main():
    logger.info(f"🔐 Secure WebSocket server on wss://0.0.0.0:{PORT}")
    async with websockets.serve(handle_connection, "0.0.0.0", PORT, ssl=ssl_context):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
