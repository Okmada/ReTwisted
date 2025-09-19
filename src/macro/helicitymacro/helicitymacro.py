import time
from typing import Type

import cv2
import numpy as np

import simplecv as scv
from controller import Controller
from macro.macro import Macro, ensure_n_times, fail_n_times, safe_execution
from macro.twistedmacro.twistedmacro_1_19_1 import ODRTwisted_1_19_1


class Colors:
    BLUE_LOGO = (212, 52, 81)
    GREEN_PLAY = (98, 182, 104)


class HelicityMacro(Macro):
    PLACE_ID = "17759606919"

    class Data(Macro.Data):
        FORMAT = {
            "RISK": str,

            "LAPSE RATES": float,
            "DEW POINT": int,
            "CAPE": int,
            "WIND SHEAR": int,
            "RELATIVE HUMIDITY": int,
        }

    @property
    def steps(self):
        return[
            self.await_menu,
            self.click_menu,
            self.await_select,
            self.select_spawn,
            self.open_thermos,
            self.get_data
        ]

    @ensure_n_times(n=5)
    def await_menu(self, img: np.ndarray) -> bool:
        # WAIT FOR MENU AND CLICK PLAY
        H, W, *_ = img.shape

        return bool(np.all(img[int(H * 0.175 + W * 0.25 * 0.2), int(W * 0.175)] == Colors.BLUE_LOGO).any())
    
    def click_menu(self, img: np.ndarray) -> bool:
        H, W, *_ = img.shape

        point = (0.175 * W, 0.466 * H)
        Controller().sync_click(self.roblox.hwnd, self.roblox.offset_point(point))

        return True
    
    @ensure_n_times(n=3)
    def await_select(self, img: np.ndarray) -> bool:
        return scv.has_color(img, Colors.GREEN_PLAY)
    
    def select_spawn(self, img: np.ndarray) -> bool:
        # SELECT SPAWN
        H, W, *_ = img.shape

        point = (0.5 * W, 0.9 * H)

        Controller().sync_click(self.roblox.hwnd, self.roblox.offset_point(point))

        time.sleep(5)

        return True

    def open_thermos(self, img: np.ndarray) -> bool:
        # OPEN MENU AND CLICK THERMOS BUTTON
        H, W, *_ = img.shape

        point = (5, 0.5 * H)

        Controller().sync_click(self.roblox.hwnd, self.roblox.offset_point(point))

        time.sleep(1.5)

        icon_size = round(0.04 * W)
        point = (0.0167 * W + icon_size / 2, 0.53 * H + icon_size)

        Controller().sync_click(self.roblox.hwnd, self.roblox.offset_point(point))

        time.sleep(1)

        return True

    @safe_execution
    @fail_n_times(n=5)
    def get_data(self, img: np.ndarray) -> False | Type[Data]:
        data_output = {}
        data_format_iterator = iter(self.Data.FORMAT.items())

        H, W, *_ = img.shape

        cutout = cv2.cvtColor(img[round(0.20 * H):round(0.85 * H), round(0.4 * W)+1:round(0.6 * W)-1], cv2.COLOR_BGR2GRAY)
        cutout[cutout<=127] = 0

        rows_mask = np.zeros_like(cutout)
        rows_mask[np.where(cutout.max(axis=1)>0)[0]] = 255

        rows_contours = scv.find_contours(rows_mask)
        rows_contours.sort(key=lambda e: scv.get_contour_center(e)[1])

        risk_data, _, *other_data = rows_contours

        risk_img = scv.extract_contour(cutout, risk_data)
        risk_img = scv.crop_image(risk_img)
        risk_img = scv.crop_image(risk_img[:, round(risk_img.shape[0] * 2.75):])

        # ratio = risk_img.shape[1] / risk_img.shape[0]
        # print(ratio)

        # if ratio < 6:
        #     risk_txt = "HIGH"
        # elif ratio < 9:
        #     risk_txt = "SLIGHT"
        # elif ratio < 9.5:
        #     risk_txt = "MARGINAL"
        # else:
        #     risk_txt = "ENHANCED"

        data_name, data_type = next(data_format_iterator)
        data_output[data_name] = "WIP"

        other_data_iter = iter(other_data)
        unit_coef_iter = iter([
            1.3, # LAPSE RATE
            1.3, # DEW POINT
            2.3, # CAPE
            1.6, # WIND SHEAR
            1.1, # RELATIVE HUMIDITY
        ])

        for text_con, number_con, coef in zip(*[other_data_iter] * 2, unit_coef_iter):
            number_img = scv.extract_contour(cutout, number_con)
            number_img = scv.crop_image(number_img)
            number_img = number_img[:, :-round(number_img.shape[0] * coef)]
            
            data_name, data_type = next(data_format_iterator)
            data_output[data_name] = scv.read_number(ODRTwisted_1_19_1(), number_img, data_type)

        return self.Data(**data_output), {"image": cutout}