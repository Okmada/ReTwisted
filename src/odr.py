import cv2
import numpy as np

from utils import Singleton, resource_path

SAMPLES_FILE = "assets/samples.data"
RESPONSES_FILE = "assets/responses.data"

class ODR(metaclass=Singleton):
    def __init__(self):
        self.model = cv2.ml.KNearest.create()

        self.samples = np.ndarray((0, 100), np.float32)
        self.responses = np.ndarray((0, 1), np.float32)

    def load(self) -> None:
        self.samples = np.loadtxt(resource_path(SAMPLES_FILE), np.float32)
        self.responses = np.loadtxt(resource_path(RESPONSES_FILE), np.float32)
        self.responses = self.responses.reshape((self.responses.size, 1))

    def save(self) -> None:
        np.savetxt(resource_path(SAMPLES_FILE), self.samples)
        np.savetxt(resource_path(RESPONSES_FILE), self.responses)

    def append(self, sample: np.ndarray, response: int) -> None:
        np.append(self.samples, self.prepare_for_odr(sample))
        np.append(self.responses, response)

    def train(self) -> None:
        self.model.train(samples=self.samples, responses=self.responses, layout=cv2.ml.ROW_SAMPLE)

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
