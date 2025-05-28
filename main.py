import asyncio
import ssl
import websockets
from led import LED, Color
from button import Button
import json
import logging 


logger = logging.getLogger(__name__)
#logging.basicConfig(filename='logs/example.log', encoding='utf-8', level=logging.DEBUG)
                    
PORT = 8765
CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"

LEDs = (
    LED(pin_r=14, pin_g=18, pin_b=19),  # Example LED on GPIO pins
    LED(pin_r=21, pin_g=22, pin_b=23),    # Another LED on different GPIO pins
    LED(pin_r=25, pin_g=26, pin_b=27),   # And another one
    # LED(pin_r=29, pin_g=37, pin_b=36),     # Yet another LED
)
Buttons = (
    Button(id=1, pin=16),  # Button on GPIO pin 16
    Button(id=2, pin=20), # Another button on GPIO pin 12
    Button(id=3, pin=24), # And another button on GPIO pin 16
    Button(id=4, pin=28), # Yet another button on GPIO pin 20
)


# Create the SSL context
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

# Client handler
async def handle_connection(websocket):
    logger.info(f"[+] Secure connection from {websocket.remote_address}")
    for button in Buttons:
        button.socket = websocket
    try:
        async for message in websocket:
            logger.debug(f"[>] {message}")
            try:
                data = json.loads(message)
                if 'command' in data:
                    command = data['command']
                    led_index = data.get('led_index', 0) -1  # Convert to zero-based index
                    if command == 'set_color':
                        color = data.get('color', {'r': 0, 'g': 0, 'b': 0})
                        if 0 <= led_index < len(LEDs):
                            color_obj = Color(color['r'], color['g'], color['b'])
                            LEDs[led_index].set_color(color_obj)
                            await websocket.send(f"LED {led_index} color set to {color}")
                        else:
                            await websocket.send("Invalid LED index")
                    elif command == 'toggle':
                        if 0 <= led_index < len(LEDs):
                            LEDs[led_index].toggle()
                            await websocket.send(f"LED {led_index} toggled")
                        else:
                            await websocket.send("Invalid LED index")
                    elif command == 'on':
                        if 0 <= led_index < len(LEDs):
                            LEDs[led_index].on()
                            await websocket.send(f"LED {led_index} turned ON")
                        else:
                            await websocket.send("Invalid LED index")
                    elif command == 'off':
                        if 0 <= led_index < len(LEDs):
                            LEDs[led_index].off()
                            await websocket.send(f"LED {led_index} turned OFF")
                        else:
                            await websocket.send("Invalid LED index")
                    else:
                        await websocket.send("Unknown command")
                else:
                    await websocket.send("No command provided")
            except json.JSONDecodeError:
                await websocket.send("Invalid JSON format")
            await websocket.send(f"Echo: {message}")
    except websockets.ConnectionClosed:
        logger.info(f"[-] Connection closed from {websocket.remote_address}")
        for button in Buttons:
            button.socket = None

# Main event loop
async def main():
    logger.info(f"🔐 Secure WebSocket server on wss://0.0.0.0:{PORT}")
    async with websockets.serve(handle_connection, "0.0.0.0", PORT, ssl=ssl_context):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
