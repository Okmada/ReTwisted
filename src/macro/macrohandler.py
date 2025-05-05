import logging
import threading
import time
from typing import Any, Callable

import enum
from config import ConfigManager
from data import Data
from discord import Webhook
from macro.macros import Macros, DefaultMacro
from roblox import Roblox
from datalogger import DataLogger

class States(enum.Enum):
    START_ROBLOX = enum.auto()
    AWAIT_ROBLOX = enum.auto()
    RUN_MACRO = enum.auto()

class MacroHandler(threading.Thread):
    def __init__(self, roblox: Roblox, webhook: Webhook) -> None:
        super().__init__(daemon=True, name=roblox.friendly_name)

        self.pause_event = threading.Event()

        self.roblox = roblox
        self.webhook = webhook

        self._macro = Macros[DefaultMacro](self.roblox)

        self._state = States.START_ROBLOX

        self._time = None
        self._last_frame_time = None
        self._data_callbacks = []
        self._pause_callbacks = []
        self._last_data = None

        self.start()

    def change_macro(self, macro: str):
        if macro in Macros:
            self._macro = Macros[macro](self.roblox)
            self.restart()

    def run(self):
        while True:
            try:
                self.pause_event.wait()

                if self.is_timedout():
                    raise Exception("Time for reroll exceeded limit (timeout)")

                match (self._state):
                    case (States.START_ROBLOX):
                        linkCode = ConfigManager().get(["roblox", self.roblox.name, "server"])
                        self.roblox.join_place(self._macro.PLACE_ID, linkCode)

                        self._state = States.AWAIT_ROBLOX
                        continue

                    case (States.AWAIT_ROBLOX):
                        if (self.roblox.hwnd != 0):
                            self._state = States.RUN_MACRO
                        else:
                            time.sleep(1)
                        continue

                    case (States.RUN_MACRO):
                        if self.roblox.is_crashed():
                            raise Exception("Roblox crashed")
                        
                        time_now = time.time()
                        time_delta = time_now - (self._last_frame_time or 0)
                        time_to_sleep = (1 / 2) - time_delta

                        if time_to_sleep > 0:
                            time.sleep(time_to_sleep)
        
                        if (frame := self.roblox.get_frame()) is None:
                            continue
                        self._last_frame_time = time_now

                        return_val = self._macro(frame)

                        if isinstance(return_val, bool):
                            continue

                        data, webhook_images = return_val

                        if self._last_data == data:
                            raise Exception("Same data as previous roll, restarting roblox")
                        self._last_data = data

                        logging.info(data)

                        if ConfigManager().get(["save data"]):
                            DataLogger.append(data, "%s-data.csv" % self._macro.__class__.__name__)

                        if self.check_conditions(data):
                            logging.info("Conditions passed")

                            self.webhook.send(macro=self._macro.__class__, data=data, roblox_type=self.roblox.name, webhook_images=webhook_images)

                            for f in self._pause_callbacks: f()

                        self.restart()
            except Exception as e:
                logging.exception(e)

                self.roblox.close_roblox()
                time.sleep(5)
                self.restart()

    def pause(self) -> None:
        self.pause_event.clear()

    def unpause(self) -> None:
        if ConfigManager().get(["roblox", self.roblox.name, "enabled"]):
            self._time = time.time()

            self.pause_event.set()

    def restart(self):
        self._state = States.START_ROBLOX
        self._macro.restart()
        self._time = time.time()

    def is_timedout(self) -> bool:
        time_max = ConfigManager().get(["timeout"])

        if not time_max:
            return False

        return time.time() - self._time > time_max if time_max else False

    def add_data_callback(self, func: Callable[[Data], Any]) -> None:
        self._data_callbacks.append(func)

    def add_pause_callback(self, func: Callable[[], Any]) -> None:
        self._pause_callbacks.append(func)

    def check_conditions(self, data: Data) -> bool:
        for group in ConfigManager().get(["conditions", self._macro.__class__.__name__]):
            for condition in group:
                what, comparison_type, expected_data = condition

                real_data = data[what]
                expected_data = type(real_data)(expected_data)

                if comparison_type == "==" and real_data != expected_data:
                    break
                elif comparison_type == ">=" and real_data < expected_data:
                    break
                elif comparison_type == "<=" and real_data > expected_data:
                    break
            else:
                return True
        return False
