import json

import cv2
import numpy as np

from utils import Singleton, resource_path


class ODR(metaclass=Singleton):
    SAMPLES_FILE = "assets/samples.data"

    def __init__(self):
        self.model = cv2.ml.KNearest.create()

        self.samples = []

    def load(self) -> None:
        with open(resource_path(self.SAMPLES_FILE), "r") as file:
            self.samples = json.load(file)

    def save(self) -> None:
        with open(resource_path(self.SAMPLES_FILE), "w") as file:
            json.dump(self.samples, file)

    def append(self, sample: np.ndarray, response: int) -> None:
        self.samples.append(sample + [response])

    def train(self) -> None:
        npSamples = np.array(self.samples).astype(np.float32)
        self.model.train(samples=npSamples[:, :-1], responses=npSamples[:, -1:], layout=cv2.ml.ROW_SAMPLE)

    def detect(self, sample: np.ndarray) -> int:
        prepped = self.prepare_for_odr(sample)
        retval, results, neigh_resp, dists = self.model.findNearest(prepped, k=1)
        # print(int(results[0][0]))
        return int(results[0][0])

    def prepare_for_odr(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        resize = cv2.resize(gray, (10, 10))
        reshape = resize.reshape((1,100))
        return reshape.astype(np.float32)
