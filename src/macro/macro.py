import functools
import logging
import time
from typing import List, Type

import numpy as np

from controller import Controller
from data import Data
from roblox import Roblox

CHAT_COLOR = (241, 239, 239)
CHAT_BB = {"left": 126, "top": 23, "right": 150, "bottom": 45}

class PhaseError(Exception):
    def __init__(self, phase: int) -> None:
        super().__init__(f"Encountered exception in phase {phase}")

class Macro:
    PLACE_ID = None

    class Data(Data):
        pass

    def __init__(self, roblox: Roblox) -> None:
        self.roblox = roblox

        self._passes = 0
        self._fails = 0
        self._phase = 0

    def __call__(self, *args, **kwargs) -> bool | Type[Data]:
        func = self.steps[self._phase]

        try:
            return_val = func(*args, **kwargs)
        except Exception as e:
            raise PhaseError(self._phase) from e

        assert return_val is not None, "Return value is None"

        pass_n, pass_delay = getattr(func, "ensure", (1, None))
        fail_n, fail_delay, fail_increment = getattr(func, "max_tries", (None, None, None))

        if return_val:
            self._passes += 1
            self._fails = 0

            if self._passes >= pass_n:
                self._passes = 0
                self._fails = 0

                self._chnage_phase(1)
            else:
                time.sleep(pass_delay)
        else:
            self._passes = 0
            self._fails += 1

            if fail_n is not None:
                if self._fails >= fail_n:
                    self._passes = 0
                    self._fails = 0

                    self._chnage_phase(fail_increment)
                else:
                    time.sleep(fail_delay)

        return return_val

    @property
    def steps(self) -> List:
        raise NotImplementedError

    def restart(self) -> None:
        self._phase = 0

    def _chnage_phase(self, increment: int) -> None:
        self._phase += increment
        self._phase %= len(self.steps)

    def close_chat(self, img: np.ndarray) -> bool:
        chat_slice = img[CHAT_BB["top"]:CHAT_BB["bottom"], CHAT_BB["left"]:CHAT_BB["right"]]
        ratio = np.count_nonzero(np.all(chat_slice == CHAT_COLOR, axis=2)) / np.multiply(*chat_slice.shape[:2])

        if ratio >= .25:
            point = ((CHAT_BB["left"] + CHAT_BB["right"]) // 2, (CHAT_BB["top"] + CHAT_BB["bottom"]) // 2)
            Controller().sync_click(self.roblox.hwnd, self.roblox.offset_point(point))
        return True

def ensure_n_times(n: int, delay: float):
    def wrapper(func):
        func.ensure = (n, delay)
        return func
    return wrapper

def fail_n_times(n: int, delay: float, steps_return: int):
    def wrapper(func):
        func.max_tries = (n, delay, steps_return)
        return func
    return wrapper

def safe_execution(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.info("Exception in safe execute: " + str(e))
            return False
    return wrapper
