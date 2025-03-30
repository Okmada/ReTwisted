class Data(dict):
    FORMAT = {}

    def __init__(self, **data):
        super().__init__({name: data_type(data[name])
                          for (name, data_type)
                          in self.FORMAT.items()})
