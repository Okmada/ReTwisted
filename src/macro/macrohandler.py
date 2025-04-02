import logging
import threading
import time
from typing import Any, Callable

from config import ConfigManager
from controller import Controller
from data import Data
from discord import Webhook
from macro.macros import Macros
from roblox import Roblox


class MacroHandler(threading.Thread):
    def __init__(self, roblox: Roblox, controller: Controller, webhook: Webhook) -> None:
        super().__init__(daemon=True, name=roblox.friendly_name)

        self.pause_event = threading.Event()

        self.roblox = roblox
        self.controller = controller
        self.webhook = webhook

        self._macro_name = None
        self._macro = None

        self._time = None
        self._data_callbacks = []
        self._pause_callbacks = []

        self.start()

    def change_macro(self, macro: str):
        if macro in Macros:
            self._macro_name = macro
            self._macro = Macros[macro](self.roblox, self.controller)

    def run(self):
        while True:
            try:
                self.pause_event.wait()

                if self._macro_name is None or self._macro is None:
                    logging.error("No macro selected")
                    time.sleep(5)
                    continue

                if self.is_timedout():
                    raise Exception("Time for reroll exceeded limit (timeout)")

                if self.roblox.is_crashed():
                    raise Exception("Roblox crashed")

                img = self.roblox.get_screenshot()

                return_val = self._macro(img)

                if isinstance(return_val, bool):
                    continue

                data, webhook_images = return_val

                logging.info(data)

                for f in self._data_callbacks: f(data)

                if self.check_conditions(data):
                    logging.info("Conditions passed")

                    self.webhook.send(roblox_type=self.roblox.name, data=data, webhook_images=webhook_images)

                    for f in self._pause_callbacks: f()

                self._time = time.time()
            except Exception as e:
                logging.exception(e)

                self.roblox.close_roblox()

                time.sleep(5)

                self._macro.restart()
                self._time = time.time()

    def pause(self) -> None:
        self.pause_event.clear()

    def unpause(self) -> None:
        if ConfigManager().get(["roblox", self.roblox.name, "enabled"]):
            self._time = time.time()

            self.pause_event.set()

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
        for group in ConfigManager().get(["conditions", self._macro_name]):
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
