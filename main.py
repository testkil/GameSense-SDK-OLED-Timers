import json
import os
import signal
import sys
import threading
import time
from datetime import datetime, timedelta

import requests
from PIL import Image
from pynput import keyboard
from pystray import Icon, MenuItem, Menu

def get_core_props():
    """Fetch core properties from the SteelSeries Engine configuration."""
    program_data = os.getenv('PROGRAMDATA')
    core_props_path = os.path.join(program_data, 'SteelSeries', 'SteelSeries Engine 3', 'coreProps.json')
    try:
        with open(core_props_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise Exception('coreProps.json not found. Ensure SteelSeries Engine is running.')

def register_app(address):
    """Register the application with SteelSeries Engine."""
    json_payload = {
        "game": "TIMERS",
        "game_display_name": "Timer App",
        "developer": "Axelle Camacho"
    }
    requests.post(f'http://{address}/game_metadata', json=json_payload)

def bind_event(address):
    """Register an event handler for displaying text."""
    json_payload = {
        "game": "TIMERS",
        "event": "DISPLAY_TEXT",
        "handlers": [{
            "device-type": "screened",
            "zone": "one",
            "mode": "screen",
            "datas": [
                {
                    "lines": [
                        {
                            "has-text": True,
                            "context-frame-key": "first-line",

                        },
                        {
                            "has-text": True,
                            "context-frame-key": "second-line",
                        }
                        ,
                        {
                            "has-text": True,
                            "context-frame-key": "third-line",
                        }
                    ]
                }
            ]
        }]
    }
    requests.post(f'http://{address}/bind_game_event', json=json_payload)

def bind_end_notification_event(address):
    """Register an event handler for full-screen timer end notification."""
    json_payload = {
        "game": "TIMERS",
        "event": "TIMER_END_NOTIFICATION",
        "handlers": [{
            "device-type": "screened",
            "zone": "one",
            "mode": "screen",
            "datas": [
                {
                    "has-text": True,
                    "context-frame-key": "notification-text",
                    "icon-id": 36
                }
            ]
        }]
    }
    requests.post(f'http://{address}/bind_game_event', json=json_payload)

def trigger_event(address, timers):
    """Trigger the event to display the specified message."""
    line1 = f"{timers[0]}" if len(timers) > 0 else " "
    line2 = f"{timers[1]}" if len(timers) > 1 else " "
    line3 = f"{timers[2]}" if len(timers) > 2 else " "
    json_payload = {
        "game": "TIMERS",
        "event": "DISPLAY_TEXT",
        "data": {
            "value": timers,
            "frame": {
                "first-line": line1,
                "second-line": line2,
                "third-line": line3
            }
        }
    }
    requests.post(f'http://{address}/game_event', json=json_payload)

def trigger_end_notification(address):
    """Trigger the event to display a full-screen timer end notification."""
    json_payload = {
        "game": "TIMERS",
        "event": "TIMER_END_NOTIFICATION",
        "data": {
            "value": datetime.now().strftime("%H:%M:%S"),
            "frame": {
                "notification-text": f"SITE SPAWN "
            }
        }
    }
    requests.post(f'http://{address}/game_event', json=json_payload)

def cleanup(address):
    """Cleanup by de-registering the application."""
    json_payload = {"game": "TIMERS"}
    requests.post(f'http://{address}/remove_game', json=json_payload)

def signal_handler(signum, frame):
    """Handle graceful shutdown."""
    try:
        core_props = get_core_props()
        address = core_props['address']
        cleanup(address)
    finally:
        os._exit(0)  # Ensure the program exits

timers = []
timer_end_times = []
max_timers = 3
core_props = get_core_props()
address = core_props['address']
timer_running = True

def start_timer():
    """Start a new 7-minute timer."""
    if len(timers) < max_timers:
        timers.append("")
        timer_end_times.append(datetime.now() + timedelta(minutes=7, seconds=10))

def reset_timers():
    """Reset all timers."""
    global timer_running
    timers.clear()
    timer_end_times.clear()
    trigger_event(address, timers)

def timer_tick():
    """Main timer loop to update all timers."""
    global timer_running
    while timer_running:
        now = datetime.now()
        update_timers = True
        for index, end_time in enumerate(timer_end_times):
            remaining = (end_time - now).total_seconds()
            if remaining > 1:
                minutes, seconds = divmod(int(remaining), 60)
                timer_text = f"Timer {index + 1}: {minutes:02}:{seconds:02}"
                timers[index] = timer_text
            else:
                trigger_end_notification(address)
                time.sleep(3)
                timers[index] = ""
                timer_end_times[index] = None
                update_timers = False
        if update_timers and len(timer_end_times) > 0:
            trigger_event(address, timers)

        # Remove ended timers
        while None in timer_end_times:
            index = timer_end_times.index(None)
            timer_end_times.pop(index)
            timers.pop(index)

        time.sleep(1)

def on_press(key):
    """Handle key press events to start and stop timers."""
    try:
        if key == keyboard.HotKey.parse('<ctrl>+<alt>+s'):
            start_timer()
        elif key == keyboard.HotKey.parse('<ctrl>+<alt>+r'):
            reset_timers()
    except AttributeError:
        pass

def create_system_tray_icon():
    """Creates and starts the system tray icon."""
    icon_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    icon_image = Image.open(os.path.join(icon_path, "stopwatch.ico"))
    menu = Menu(MenuItem("Exit", on_exit))
    icon = Icon("TimerApp", icon_image, "Timer Application", menu)
    icon.run()

def on_exit(icon, item):
    """Handles the exit action from the system tray."""
    icon.stop()
    global timer_running
    timer_running = False
    signal_handler(None, None)  # Ensure cleanup and exit

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    system_tray_thread = threading.Thread(target=create_system_tray_icon)
    system_tray_thread.start()

    try:
        register_app(address)
        bind_event(address)
        bind_end_notification_event(address)

        hotkeys = {
            '<ctrl>+<alt>+s': start_timer,
            '<ctrl>+<alt>+r': reset_timers
        }

        with keyboard.GlobalHotKeys(hotkeys) as h:
            listener = keyboard.Listener(on_press=on_press)
            listener.start()

            # Start the timer thread
            global timer_running
            timer_running = True
            timer_thread = threading.Thread(target=timer_tick)
            timer_thread.start()

            listener.join()
            timer_thread.join()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
