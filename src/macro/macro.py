from typing import List, Type

from config import ConfigManager
from controller import Controller
from data import Data
from roblox import Roblox


class Macro:
    def __init__(self, roblox: Roblox, controller: Controller, config: ConfigManager) -> None:
        self.roblox = roblox
        self.controller = controller
        self.config = config

        self._phase = 0

    def __call__(self, *args, **kwargs) -> bool | Type[Data]:
        func = self.steps[self._phase]
        return_val = func(*args, **kwargs)

        assert return_val is not None, "Return value is None"

        if return_val:
            self._phase += 1
            self._phase %= len(self.steps)

        return return_val

    @property
    def steps(self) -> List:
        raise NotImplementedError

    def restart(self) -> None:
        self._phase = 0
