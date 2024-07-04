import logging
import threading
import time
from typing import Any, Callable

from config import ConfigManager
from controller import Controller
from data import Data
from discord import Webhook
from macro.twistedmacro import TwistedMacro
from roblox import Roblox


class MacroHandler(threading.Thread):
    def __init__(self, roblox: Roblox, controller: Controller, config: ConfigManager, webhook: Webhook) -> None:
        super().__init__(daemon=True, name=roblox.friendly_name)

        self.pause_event = threading.Event()

        self.roblox = roblox
        self.controller = controller
        self.config = config
        self.webhook = webhook

        self._macro = TwistedMacro(roblox, controller, config)

        self._time = None
        self._data_callbacks = []
        self._pause_callbacks = []

        self.start()

    def run(self):
        while True:
            try:
                self.pause_event.wait()

                if self.is_timedout():
                    raise Exception("Time for reroll exceeded limit (timeout)")

                if self.roblox.is_crashed():
                    raise Exception("Roblox crashed")

                img = self.roblox.get_screenshot()

                return_val = self._macro.get(img)

                if isinstance(return_val, bool):
                    continue

                data, data_img, code_img = return_val

                logging.info(data)

                if self.check_conditions(data):
                    logging.info("Conditions passed")

                    self.webhook.send(roblox_type=self.roblox.name, data=data, data_image=data_img, code_image=code_img)

                    [f() for f in self._pause_callbacks]

                self._time = time.time()
            except Exception as e:
                logging.error(f"Encountered exception in phase {self._macro._phase}")
                logging.error(str(e))

                self._macro.restart()
                self._time = time.time()

    def pause(self) -> None:
        self.pause_event.clear()

    def unpause(self) -> None:
        if self.config.get([self.roblox.name, "enabled"]):
            self._time = time.time()

            self.pause_event.set()

    def is_timedout(self) -> bool:
        time_max = self.config.get(["timeout"])

        if not time_max:
            return False

        return time.time() - self._time > time_max if time_max else False

    def add_data_callback(self, func: Callable[[Data], Any]) -> None:
        self._data_callbacks.append(func)

    def add_pause_callback(self, func: Callable[[], Any]) -> None:
        self._pause_callbacks.append(func)

    def check_conditions(self, data: Data) -> bool:
        for group in self.config.get(["conditions"]):
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
