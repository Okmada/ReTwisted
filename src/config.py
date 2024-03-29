import json

class Config:
    CONFIG_FILE = ".config.json"

    def __init__(self) -> None:
        try:
            raw = json.load(open(self.CONFIG_FILE, "r"))
        except:
            raw = {}
        self.__config = raw

    def _write(self):
        with open(self.CONFIG_FILE, "w") as file:
            json.dump(self.__config, file, indent=4)
            file.close()

    def get(self, path):
        tmp = self.__config
        for arg in path:
            if arg in tmp:
                tmp = tmp[arg]
                continue
            return None
        return tmp
    
    def set(self, path, value):
        tmp = self.__config
        for i, arg in zip(range(len(path))[::-1], path):
            if i != 0:
                if arg not in tmp or type(tmp[arg]) != dict:
                    tmp[arg] = {}
                tmp = tmp[arg]
            else:
                tmp[arg] = value
        self._write()