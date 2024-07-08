import json
import os
import signal
import threading
import time
from datetime import datetime, timedelta

import requests
from pynput import keyboard


def get_core_props():
    """ Fetch core properties from the SteelSeries Engine configuration. """
    program_data = os.getenv('PROGRAMDATA')
    core_props_path = os.path.join(program_data, 'SteelSeries', 'SteelSeries Engine 3', 'coreProps.json')
    try:
        with open(core_props_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise Exception('coreProps.json not found. Ensure SteelSeries Engine is running.')


def register_app(address):
    """ Register the application with SteelSeries Engine. """
    json_payload = {
        "game": "HELLOAPP",
        "game_display_name": "Testing App",
        "developer": "Alex Camacho"
    }
    response = requests.post(f'http://{address}/game_metadata', json=json_payload)
    print("App registration response:", response.text)


def bind_event(address):
    """ Register an event handler for displaying text. """
    json_payload = {
        "game": "HELLOAPP",
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
    response = requests.post(f'http://{address}/bind_game_event', json=json_payload)
    print("Event binding response:", response.text)


def bind_end_notification_event(address):
    """ Register an event handler for full-screen timer end notification. """
    json_payload = {
        "game": "HELLOAPP",
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
    response = requests.post(f'http://{address}/bind_game_event', json=json_payload)
    print("End notification event binding response:", response.text)


def trigger_event(address, timers):
    """ Trigger the event to display the specified message. """
    line1 = f"{timers[0]}" if len(timers) > 0 else " "
    line2 = f"{timers[1]}" if len(timers) > 1 else " "
    line3 = f"{timers[2]}" if len(timers) > 2 else " "
    json_payload = {
        "game": "HELLOAPP",
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
    response = requests.post(f'http://{address}/game_event', json=json_payload)
    #print("Event trigger response:", response.text)


def trigger_end_notification(address):
    """ Trigger the event to display a full-screen timer end notification. """
    json_payload = {
        "game": "HELLOAPP",
        "event": "TIMER_END_NOTIFICATION",

        "data": {
            "value": datetime.now().strftime("%H:%M:%S"),
            "frame": {
                "notification-text": f"SITE SPAWN "
            }
        }
    }
    response = requests.post(f'http://{address}/game_event', json=json_payload)
    #print("End notification trigger response:", response.text)


def cleanup(address):
    """ Cleanup by de-registering the application. """
    json_payload = {"game": "HELLOAPP"}
    response = requests.post(f'http://{address}/remove_game', json=json_payload)
    print("Cleanup response:", response.text)


def signal_handler(signum, frame):
    """ Handle graceful shutdown. """
    print("Shutting down gracefully...")
    try:
        core_props = get_core_props()
        address = core_props['address']
        cleanup(address)
    finally:
        print("Cleanup complete. Exiting.")
        exit(0)


timers = []
timer_end_times = []
max_timers = 3
core_props = get_core_props()
address = core_props['address']
timer_running = True


def start_timer():
    """ Start a new 7-minute timer. """
    if len(timers) < max_timers:
        timers.append("")
        timer_end_times.append(datetime.now() + timedelta(minutes=7, seconds=10))


def reset_timers():
    """ Reset all timers. """
    global timer_running
    timers.clear()
    timer_end_times.clear()
    trigger_event(address, timers)


def timer_tick():
    """ Main timer loop to update all timers. """
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
                time.sleep(3)  # Display "Time's up!" for 3 seconds
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
    """ Handle key press events to start and stop timers. """
    try:
        if key == keyboard.HotKey.parse('<ctrl>+<alt>+s'):
            start_timer()
        elif key == keyboard.HotKey.parse('<ctrl>+<alt>+r'):
            reset_timers()
    except AttributeError:
        pass


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        register_app(address)
        bind_event(address)
        bind_end_notification_event(address)

        print(
            "Application running. Press Alt+S to start a 7-minute timer (up to 3 timers). Press Alt+R to reset all timers. Press Ctrl+C to stop.")

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
        print("An error occurred:", e)


if __name__ == "__main__":
    main()
