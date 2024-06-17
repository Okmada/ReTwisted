import json
import typing


class ConfigManager:
    CONFIG_FILE = ".config.json"

    def __init__(self):
        try:
            raw = json.load(open(self.CONFIG_FILE, "r"))
        except (FileNotFoundError, json.JSONDecodeError):
            raw = {}

        self.__config = ConfigGroup("", [
            *[
                ConfigGroup(roblox_type, [
                    ConfigValue("enabled", bool, False),
                    ConfigValue("server", str, ""),
                ])
                for roblox_type in ["WINDOWSCLIENT", "ApplicationFrameWindow"]
            ],
            ConfigGroup("webhook", [
                ConfigValue("url", str, ""),
                ConfigValue("role id", str, ""),
                ConfigValue("user id", str, ""),
            ]),
            ConfigValue("timeout", int, 75),
            ConfigValue("resume timer", int, 15),
            ConfigValue("save data", bool, True),
            ConfigValue("conditions", list, []),
        ])

        self.__config.set(raw)

    def _write(self):
        with open(self.CONFIG_FILE, "w") as file:
            json.dump(self.__config.get(), file, indent=4)

    def get(self, path):
        tmp = self.__config
        for arg in path:
            tmp = tmp.find(arg)
        return tmp.get()
    
    def set(self, path, value):
        tmp = self.__config
        for arg in path:
            tmp = tmp.find(arg)
        tmp.set(value)

        self._write()

class ConfigTemplate:
    def __init__(self):
        self.name = "TEMPLATE"

    def get(self):
        raise NotImplementedError("Subclasses should implement this method")
    
    def set(self, value):
        raise NotImplementedError("Subclasses should implement this method")
    
    def find(self, name):
        raise NotImplementedError("Subclasses should implement this method")
    
class ConfigGroup(ConfigTemplate):
    def __init__(self, name: str, subconfigs: list[ConfigTemplate]):
        """
        Initialize a configuration group.

        Args:
            name (str): The name of the configuration group.
            subconfigs (list[ConfigTemplate]): A list of subconfigurations.

        Raises:
            AssertionError: If there are duplicate configuration names in the group.
        """
        self.name = name.lower()
        self.subconfigs = {config.name: config for config in subconfigs}

        assert len(subconfigs) == len(self.subconfigs), "Duplicate configs in group"

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
            raise KeyError(f"Configuration '{name}' not found in group '{self.name}'")

        return self.subconfigs[name]


class ConfigValue(ConfigTemplate):
    def __init__(self, name: str, dtype: typing.Type, dvalue: typing.Any):
        """
        Initialize a configuration value.

        Args:
            name (str): The name of the configuration value.
            dtype (typing.Type): The expected data type of the value.
            dvalue (typing.Any): The default value of the configuration.

        Raises:
            AssertionError: If the default value type does not match the expected data type.
        """
        assert isinstance(dvalue, dtype), "Default value type does not match data type"

        self.name = name.lower()
        self.dtype = dtype
        self.dvalue = dvalue
        self.value = dvalue

    def get(self) -> typing.Any:
        """
        Get the current value.

        Returns:
            typing.Any: The current value.
        """
        return self.value

    def set(self, value: typing.Any) -> bool:
        """
        Set a new value.

        Args:
            value (typing.Any): The new value to be set.

        Returns:
            bool: True if the value was set successfully, False otherwise.
        """
        if not isinstance(value, self.dtype) or value is None:
            self.value = self.dvalue
            return False
        
        self.value = value
        return True
