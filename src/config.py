import json
from typing import Any, List, Type

from utils import Singleton


class ConfigManager(metaclass=Singleton):
    CONFIG_FILE = "config.json"

    def __init__(self):
        try:
            raw = json.load(open(self.CONFIG_FILE, "r", encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            raw = {}

        self.__config = ConfigGroup({
            "roblox": ConfigGroup({
                roblox_type: ConfigGroup({
                    "enabled": ConfigValue(bool, False),
                    "macro": ConfigValue(str, ""),
                })
                for roblox_type in ("WINDOWSCLIENT", "ApplicationFrameWindow")
            }),
            "macros": ConfigGroup({
                macro: ConfigGroup({
                    "server": ConfigGroup({
                        "microsoft roblox": ConfigValue(str, ""),
                        "roblox player": ConfigValue(str, ""),
                    }),
                    "conditions": ConfigValue(list, []),
                })
                for macro in ["TwistedMacro_latest", "TwistedMacro_1_19_1"]
            }),
            "webhook": ConfigGroup({
                "url": ConfigValue(str, ""),
                "share link": ConfigValue(bool, True),
                "role id": ConfigValue(str, ""),
                "user id": ConfigValue(str, ""),
            }),
            "leave after roll": ConfigGroup({
                "enabled": ConfigValue(bool, False),
                "time": ConfigValue(int, 5),
            }),
            "timeout": ConfigValue(int, 75),
            "resume timer": ConfigValue(int, 15),
            "save data": ConfigValue(bool, True),
            "restart on duplicate data": ConfigValue(bool, True),
            "roblox player launcher override": ConfigValue(str, ""),
        })

        self.__config.set(raw)

    def _write(self) -> None:
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(self.__config.get(), file, indent=4)

    def get(self, path: List[str]) -> Any:
        tmp = self.__config
        for arg in path:
            tmp = tmp.find(arg)
        return tmp.get()

    def set(self, path: List[str], value: Any) -> None:
        tmp = self.__config
        for arg in path:
            tmp = tmp.find(arg)
        tmp.set(value)

        self._write()

class ConfigTemplate:
    def get(self):
        raise NotImplementedError("Subclasses should implement this method")

    def set(self, value: Any):
        raise NotImplementedError("Subclasses should implement this method")

    def find(self, name: str):
        raise NotImplementedError("Subclasses should implement this method")

class ConfigGroup(ConfigTemplate):
    def __init__(self, subconfigs: dict[str, ConfigTemplate]):
        """
        Initialize a configuration group.

        Args:
            subconfigs (dict[str, ConfigTemplate]): A dict of names and subconfigurations.
        """
        self.subconfigs = {name.lower(): config for name, config in subconfigs.items()}

    def get(self) -> dict:
        """
        Get the configuration values.

        Returns:
            dict: A dictionary of configuration names and their values.
        """
        return {name: config.get() for name, config in self.subconfigs.items()}

    def set(self, value: dict) -> bool:
        """
        Set the configuration values.

        Args:
            value (dict): A dictionary of configuration names and their new values.

        Returns:
            bool: True if the values were set successfully, False otherwise.
        """
        if not isinstance(value, dict):
            return False

        for name, config in self.subconfigs.items():
            if name in value:
                config.set(value[name])

        return True

    def find(self, name: str) -> ConfigTemplate:
        """
        Find a configuration by name.

        Args:
            name (str): The name of the configuration to find.

        Returns:
            ConfigTemplate: The configuration object.

        Raises:
            KeyError: If the configuration name is not found.
        """
        name = name.lower()

        if name not in self.subconfigs:
            raise KeyError(f"Configuration '{name}' not found in group '{self}'")

        return self.subconfigs[name]


class ConfigValue(ConfigTemplate):
    def __init__(self, dtype: Type, dvalue: Any):
        """
        Initialize a configuration value.

        Args:
            dtype (Type): The expected data type of the value.
            dvalue (Any): The default value of the configuration.

        Raises:
            AssertionError: If the default value type does not match the expected data type.
        """
        assert isinstance(dvalue, dtype), "Default value type does not match data type"

        self.dtype = dtype
        self.dvalue = dvalue
        self.value = dvalue

    def get(self) -> Any:
        """
        Get the current value.

        Returns:
            Any: The current value.
        """
        return self.value

    def set(self, value: Any) -> bool:
        """
        Set a new value.

        Args:
            value (Any): The new value to be set.

        Returns:
            bool: True if the value was set successfully, False otherwise.
        """
        if not isinstance(value, self.dtype) or value is None:
            self.value = self.dvalue
            return False

        self.value = value
        return True
