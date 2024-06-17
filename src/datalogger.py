import datetime
import logging

from macro import Data


class DataLogger:
    FILENAME = "data.csv"
    LABELS = ["DATETIME"] + list(Data.FORMAT.keys())

    def __init__(self, config):
        self.config = config

    def append(self, data):
        if not self.config.get(["save data"]):
            return
        
        data = {**data, "DATETIME": datetime.datetime.now().strftime("%x %X")}

        try:
            with open(self.FILENAME, "r") as file:
                labels = file.readline().strip().split(",")

            assert all([l in labels for l in self.LABELS])
        except:
            labels = self.LABELS
            try:
                with open(self.FILENAME, "w") as file:
                    file.write(",".join(labels) + "\n")
            except Exception as e:
                logging.error(f"Failed to write new header: {e}")
                return

        try:
            with open(self.FILENAME, "a") as file:
                data_string = ",".join([str(data.get(l, "")) for l in labels])
                file.write(data_string + "\n")
        except Exception as e:
            logging.error(f"Failed to append new data: {e}")
            return
