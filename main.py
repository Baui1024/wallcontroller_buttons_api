import asyncio
import hmac
import http
import json
import logging
import math
import os

import websockets

from button import Buttons
from led import LED, Color
from mt7688gpio import MT7688GPIOAsync

# Ensure log directory exists
os.makedirs('logs', exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,  # DEBUG logs every message, too costly on this CPU
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler('logs/example.log'),
        logging.StreamHandler()  # This outputs to console
    ]
)

# Plain ws on localhost only: nginx terminates TLS on wss://<device>:8765 and
# forwards here, so certificates are handled in one place
HOST = "127.0.0.1"
PORT = 8766

# Optional token (set in the web UI) clients must send in the X-Api-Key header
SECURITY_CONFIG_FILE = "/etc/webserver/security.json"


LEDs = (
    LED(id = 2, pin_r=14, pin_g=13, pin_b=12),  #rb flipped in current revision
    LED(id = 4, pin_r=0, pin_g=1, pin_b=2),    
    LED(id = 3, pin_r=10, pin_g=9, pin_b=8),    #rgb flipped in current revision
    LED(id = 1, pin_r=4, pin_g=5, pin_b=6),
)

# LED commands only update the target state; led_writer() pushes it to the
# hardware at most every LED_FRAME_INTERVAL, so bursts of commands can't queue
# up I2C writes (latest state wins).
LED_FRAME_INTERVAL = 0.02  # max 50 hardware updates/s
led_dirty = asyncio.Event()
LED.on_change = led_dirty.set

gpio = MT7688GPIOAsync(pin=19)
gpio.set_direction(is_output=True, flip=True)  # Set pin 19 as output//OE for PCA9635
gpio.set_high()  # Set OE pin high to enable output

input_buttons = Buttons({
    1: 17,  # Button ID 1 on GPIO pin 17
    2: 14,  # Button ID 2 on GPIO pin 14
    3: 15,  # Button ID 3 on GPIO pin 15
    4: 16,  # Button ID 4 on GPIO pin 16
})


# Track active flash tasks per LED
active_flash_tasks = {}

# Track connected clients and breathing task
connected_clients = set()
breathing_task = None

async def flash_leds(data, led_index, color_obj, websocket):
    color = data.get('off_color', "#000000")
    hex_color = color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    off_color_obj = Color(r, g, b)
    length = data.get('length', 1)
    interval = data.get('interval', 0.5)
    steps = length / interval
    
    for x in range(int(steps/2)):
        for index in led_index:
            index = index - 1
            if 0 <= index < len(LEDs):
                LEDs[index].set_color(color_obj)
        await asyncio.sleep(interval)
        for index in led_index:
            index = index - 1
            if 0 <= index < len(LEDs):
                LEDs[index].set_color(off_color_obj)
        await asyncio.sleep(interval)
    
    try:
        await websocket.send(json.dumps({"success": f"Flash completed for LEDs {led_index}"}))
    except websockets.ConnectionClosed:
        pass  # Client disconnected during flash

async def led_writer():
    while True:
        await led_dirty.wait()
        led_dirty.clear()
        for led in LEDs:
            try:
                led.update_pwm()
            except OSError as e:
                logger.error(f"LED write failed: {e}")
        await asyncio.sleep(LED_FRAME_INTERVAL)

async def breathing_pattern():
    """
    Creates a breathing LED pattern across the 4 buttons.
    Layout:
        1 2
        3 4
    Pattern: Wave-like breathing that moves diagonally.
    """
    
    # LED order for the wave pattern (diagonal sweep)
    # 1 -> 2,3 -> 4
    led_order = [
        [0],      # LED 1 (top-left)
        [1, 2],   # LED 2 (top-right) and LED 3 (bottom-left)
        [3],      # LED 4 (bottom-right)
    ]
    
    base_color = Color(0, 100, 255)  # Blue breathing color
    step_delay = 0.02  # 20ms per step for smooth animation
    breath_steps = 50  # Steps for one breath cycle
    phase_offset = 0.4  # Phase offset between LED groups
    
    try:
        phase = 0.0
        while True:
            # Calculate brightness for each LED group based on phase
            for group_idx, led_group in enumerate(led_order):
                # Offset phase for each group to create wave effect
                group_phase = phase - (group_idx * phase_offset)
                # Use sine wave for smooth breathing (0 to 1)
                brightness = (math.sin(group_phase * math.pi * 2) + 1) / 2
                brightness = brightness * 0.9 + 0.1  # Keep minimum brightness at 10%
                
                # Apply to each LED in the group
                for led_idx in led_group:
                    if 0 <= led_idx < len(LEDs):
                        # Scale color by brightness
                        r = int(base_color.r * brightness)
                        g = int(base_color.g * brightness)
                        b = int(base_color.b * brightness)
                        LEDs[led_idx].set_color(Color(r, g, b))
            
            phase += 1.0 / breath_steps
            if phase >= 1.0:
                phase = 0.0
            
            await asyncio.sleep(step_delay)
    except asyncio.CancelledError:
        # Don't turn off LEDs when cancelled - let the client control them
        logger.debug("Breathing pattern cancelled")
        raise

async def start_breathing():
    global breathing_task
    if breathing_task is None or breathing_task.done():
        breathing_task = asyncio.create_task(breathing_pattern())
        logger.info("Breathing pattern started")

async def stop_breathing():
    global breathing_task
    if breathing_task and not breathing_task.done():
        breathing_task.cancel()
        try:
            await breathing_task
        except asyncio.CancelledError:
            pass
        breathing_task = None
        logger.info("Breathing pattern stopped")

def expected_token():
    """Token clients must send, or None when token authentication is off.
    Read on every connection so changes in the web UI apply immediately."""
    try:
        with open(SECURITY_CONFIG_FILE, "r") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not config.get("wsTokenEnabled") or not config.get("wsToken"):
        return None
    return config["wsToken"]

async def check_token(path, request_headers):
    """Reject the websocket handshake with 401 if the token doesn't match."""
    token = expected_token()
    if token is None:
        return None
    sent = request_headers.get("X-Api-Key", "")
    if hmac.compare_digest(sent.encode(), token.encode()):
        return None
    client = request_headers.get("X-Forwarded-For", "unknown")
    logger.warning(f"[!] Rejected connection from {client}: invalid or missing X-Api-Key")
    return (http.HTTPStatus.UNAUTHORIZED, [("Content-Type", "text/plain")], b"Invalid or missing X-Api-Key\n")

# Client handler
async def handle_connection(websocket):
    global connected_clients
    # Behind the nginx proxy the peer is always 127.0.0.1; nginx passes the real client
    remote_address = websocket.request_headers.get("X-Forwarded-For", websocket.remote_address[0])
    logger.info(f"[+] Connection from {remote_address}")
    
    # Stop breathing pattern when client connects
    connected_clients.add(websocket)
    await stop_breathing()
    
    input_buttons.socket = websocket  # Assign the WebSocket to the buttons for sending commands
    await input_buttons.open_gpio()
    try:
        async for message in websocket:
            logger.debug("[>] %s", message)
            try:
                data = json.loads(message)
                if 'command' in data:
                    command = data['command']
                    led_index = data.get('led_index', [])  # Convert to zero-based index
                    if command == 'set_color' or command == "flash":
                        color = data.get('color', "#000000")
                        hex_color = color.lstrip('#')
                        r = int(hex_color[0:2], 16)
                        g = int(hex_color[2:4], 16)
                        b = int(hex_color[4:6], 16)
                        color_obj = Color(r, g, b)
                        if command == 'set_color':
                            for index in led_index:
                                index = index - 1  # Convert to zero-based index
                                if 0 <= index < len(LEDs):
                                    LEDs[index].set_color(color_obj)
                                else:
                                    await websocket.send(json.dumps({"error": "Invalid LED index"}))
                            await websocket.send(json.dumps({"succes": f"LEDs {led_index} color set to {color}"}))
                        elif command == 'flash':
                            global active_flash_tasks
                            # Cancel any existing flash tasks for the requested LEDs
                            for index in led_index:
                                if index in active_flash_tasks and not active_flash_tasks[index].done():
                                    active_flash_tasks[index].cancel()
                                    try:
                                        await active_flash_tasks[index]
                                    except asyncio.CancelledError:
                                        pass
                            # Create a new flash task and track it for each LED
                            flash_task = asyncio.create_task(flash_leds(data, led_index, color_obj, websocket))
                            for index in led_index:
                                active_flash_tasks[index] = flash_task
                            await websocket.send(json.dumps({"success": f"Flash started for LEDs {led_index}"}))
                    elif command == 'set_brightness':
                        brightness = data.get('brightness', 1.0)
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].set_brightness(brightness)
                            else:
                                await websocket.send(json.dumps({"error": "Invalid LED index"}))
                        await websocket.send(json.dumps({"succes": f"LEDs {led_index} brightness set to {brightness}"}))
                    elif command == 'toggle':
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].toggle()
                            else:
                                await websocket.send(json.dumps({"error": "Invalid LED index"}))
                        await websocket.send(json.dumps({"succes": f"LEDs {led_index} toggled"}))
                    elif command == 'on':
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].on()
                            else:
                                await websocket.send(json.dumps({"error": "Invalid LED index"}))
                        await websocket.send(json.dumps({"succes": f"LEDs {led_index} turned ON"}))
                    elif command == 'off':
                        for index in led_index:
                            index = index - 1  # Convert to zero-based index
                            if 0 <= index < len(LEDs):
                                LEDs[index].off()
                            else:
                                await websocket.send(json.dumps({"error": "Invalid LED index"}))
                        await websocket.send(json.dumps({"succes": f"LEDs {led_index} turned OFF"}))                        
                    else:
                        await websocket.send(json.dumps({"error": "Unknown command"}))
                else:
                    await websocket.send("No command provided")
            except json.JSONDecodeError:
                await websocket.send('{"error": "Invalid JSON format"}')
    except websockets.ConnectionClosed:
        pass
    finally:
        logger.info(f"[-] Connection closed from {remote_address}")
        # Cancel any active flash tasks when connection closes
        for index, task in list(active_flash_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        active_flash_tasks.clear()
        
        # Remove client; hand button events to a remaining client, or stop
        # polling and restart breathing if none is left
        connected_clients.discard(websocket)
        if input_buttons.socket is websocket:
            input_buttons.socket = next(iter(connected_clients), None)
        if len(connected_clients) == 0:
            await input_buttons.close_gpio()
            await start_breathing()

# Main event loop
async def main():
    logger.info(f"WebSocket server on ws://{HOST}:{PORT} (TLS via nginx on :8765)")
    
    writer_task = asyncio.create_task(led_writer())  # noqa: F841 (keep a reference)

    # Commands are small JSON messages: cap message size and the per-connection
    # receive queue so a flooding client gets backpressure instead of piling up
    async with websockets.serve(handle_connection, HOST, PORT, process_request=check_token,
                                max_size=4096, max_queue=8):
        # Start breathing only once the server is listening, so the animation
        # doesn't compete for CPU with server startup during boot
        if not connected_clients:
            await start_breathing()
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
