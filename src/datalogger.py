import datetime
import logging

from data import Data


class DataLogger:
    @staticmethod
    def append(data_raw: Data, filename: str):
        labels_template = ["DATETIME"] + list(data_raw.FORMAT.keys())

        data = {**data_raw, "DATETIME": datetime.datetime.now().strftime("%x %X")}

        try:
            with open(filename, "r", encoding="utf-8") as file:
                labels = file.readline().strip().split(",")

            assert all([l in labels for l in labels_template])
        except:
            labels = labels_template
            try:
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(",".join(labels) + "\n")
            except Exception as e:
                logging.error(f"Failed to write new header: {e}")
                return

        try:
            with open(filename, "a", encoding="utf-8") as file:
                data_string = ",".join([str(data.get(l, "")) for l in labels])
                file.write(data_string + "\n")
        except Exception as e:
            logging.error(f"Failed to append new data: {e}")
            return
