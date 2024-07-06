import time
from typing import Type

import cv2
import numpy as np

import simplecv as scv
from data import Data
from macro.macro import Macro

PLACE_ID = 17759606919

class Colors:
    WHITE = (255, 255, 255)

class HelicityData(Data):
    FORMAT = {
        "RISK": str,

        "LAPSE RATES": float,
        "DEW POINT": int,
        "CAPE": int,
        "WIND SHEAR": int,
        "RELATIVE HUMIDITY": int,
    }

class HelicityMacro(Macro):
    @property
    def steps(self):
        return[
            self.start_roblox,
            self.await_menu,
            self.select_spawn,
            self.open_thermos,
            self.get_data
        ]

    def start_roblox(self, img: np.ndarray) -> bool:
        # START ROBLOX AND WAIT FOR HWND
        self.roblox.start_roblox(PLACE_ID, self.config.get(["roblox", self.roblox.name, "server"]))

        return True

    def await_menu(self, img: np.ndarray) -> bool:
        # WAIT FOR MENU AND CLICK PLAY
        H, W, *_ = img.shape

        loaded = np.all(img[58, 75] == Colors.WHITE).any()

        if loaded:
            time.sleep(5)

            point = (0.175 * W, 0.466 * H)
            self.controller.sync_click(self.roblox.hwnd, point)

        time.sleep(1)

        return loaded

    def select_spawn(self, img: np.ndarray) -> bool:
        # SELECT SPAWN
        H, W, *_ = img.shape

        point = (0.5 * W, 0.9 * H)

        self.controller.sync_click(self.roblox.hwnd, point)

        time.sleep(5)

        return True

    def open_thermos(self, img: np.ndarray) -> bool:
        # OPEN MENU AND CLICK THERMOS BUTTON
        H, W, *_ = img.shape

        point = (20, 0.45 * H)

        self.controller.sync_click(self.roblox.hwnd, point)

        time.sleep(1.5)

        point = (0.05 * W, 0.56 * H)

        self.controller.sync_click(self.roblox.hwnd, point)

        time.sleep(1)

        return True

    def get_data(self, img: np.ndarray) -> False | Type[Data]:
        data_output = []

        H, W, *_ = img.shape

        cutout = cv2.cvtColor(img[round(0.19 * H):round(0.84 * H), round(0.4 * W)+1:round(0.6 * W)-1], cv2.COLOR_BGR2GRAY)
        cutout[cutout<=127] = 0

        rows_mask = np.zeros_like(cutout)
        rows_mask[np.where(cutout.max(axis=1)>0)[0]] = 255

        rows_contours = scv.find_contours(rows_mask)
        rows_contours.sort(key=lambda e: scv.get_contour_center(e)[1])

        risk_data, _, *other_data = rows_contours

        risk_img = scv.extract_contour(cutout, risk_data)

        risk_txt = scv.read_text(risk_img).split(":")[1].strip().upper()
        data_output.append(risk_txt)

        other_data_iter = iter(other_data)
        unit_coef_iter = iter([
            1.2, # LAPSE RATE
            1.2, # DEW POINT
            2.3, # CAPE
            1.5, # WIND SHEAR
            1.1, # RELATIVE HUMIDITY
        ])

        for text_con, number_con, coef in zip(*[other_data_iter] * 2, unit_coef_iter):
            text_img = scv.extract_contour(cutout, text_con)
            number_img = scv.extract_contour(cutout, number_con)

            text_img = scv.crop_image(text_img)
            number_img = scv.crop_image(number_img)

            scale = number_img.shape[0] / text_img.shape[0]
            new_dims = [round(dim * scale) for dim in text_img.shape[:2]][::-1]

            text_img = cv2.resize(text_img, new_dims, interpolation=cv2.INTER_LINEAR)

            connected_img = np.concatenate((text_img,
                np.zeros([text_img.shape[0], round(0.5 * text_img.shape[0])], np.uint8),
                number_img[:, :-round(number_img.shape[0] * coef)]), axis=1)

            data_output.append(scv.read_number(connected_img))

        try:
            return HelicityData(*data_output), cutout, cutout
        except:
            return False
