class Data(dict):
    FORMAT = {}

    def __init__(self, *data):
        assert len(data) == len(self.FORMAT), "Invalid data len"

        super().__init__({name: data_type(value)
                          for (name, data_type), value
                          in zip(self.FORMAT.items(), data, strict=True)})
