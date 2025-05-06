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

    def prompt(self, sample: np.ndarray):
        windowName = f"Sample #{len(self.samples)}"
        
        cv2.imshow(windowName, sample)

        while (key := (cv2.waitKey(0) - ord("0"))) < 0 or key > 9:
            continue
        self.samples.append(self.prepare_for_odr(sample).flatten().tolist() + [key])

        cv2.destroyWindow(windowName)

    def detect(self, sample: np.ndarray) -> int:
        prepped = self.prepare_for_odr(sample)
        reshape = prepped.reshape((1,100)).astype(np.float32)
        retval, results, neigh_resp, dists = self.model.findNearest(reshape, k=1)
        # print(int(results[0][0]))
        return int(results[0][0])

    def prepare_for_odr(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY, image)
        return cv2.resize(image, (10, 10))
