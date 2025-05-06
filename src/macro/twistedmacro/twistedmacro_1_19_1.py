import time
from typing import Tuple, Type

import cv2
import numpy as np

import simplecv as scv
from config import ConfigManager
from controller import Controller
from macro.macro import Macro, ensure_n_times, fail_n_times, safe_execution
from odr import ODR


class ODRTwisted_1_19_1(ODR):
    SAMPLES_FILE = "assets/samples-twisted1_19_1.data"
ODRTwisted_1_19_1().load()
ODRTwisted_1_19_1().train()

class Colors:
    WHITE = (255, 255, 255)

    GRAY_0 = (25, 25, 25)
    GRAY_1 = (50, 50, 50)

    DAYS = {
        "HIGH": (255, 127, 255),
        "MRGL": (127, 197, 127),
        "SLGT": (127, 246, 246),
        "TSTM": (190, 229, 190),
        "MDT": (127, 127, 230),
        "ENH": (127, 194, 230),
    }

class TwistedMacro_1_19_1(Macro):
    PLACE_ID = "78568440332100"

    class Data(Macro.Data):
        FORMAT = {
            "C TEMPERATURE": int,
            "C DEW POINT": int,
            "C LAPSE RATE": float,
            "C HUMIDITY": int,
            "C CAPE": int,

            "F TEMPERATURE": int,
            "F DEW POINT": int,
            "F LAPSE RATE": float,
            "F HUMIDITY": int,
            "F CAPE": int,

            "DAY 1": str,
            "DAY 2": str,
            "DAY 3": str,
        }

    @property
    def steps(self):
        return[
            self.await_menu,
            self.navigate_menu,
            self.await_game,
            self.navigate_game,
            self.close_chat,
            self.open_data_menu,
            self.get_data,
        ]

    @ensure_n_times(n=5)
    def await_menu(self, img: np.ndarray) -> bool:
        # WAIT FOR TWISTED TO LOAD INTO MENU
        cutout = img[int((2/3) * img.shape[0]), ]

        return scv.has_color(cutout, Colors.GRAY_0) and scv.has_color(cutout, Colors.WHITE)

    def navigate_menu(self, img: np.ndarray) -> bool:
        # NAVIGATE MENU
        play_button = self.roblox.offset_point((int(0.5 * img.shape[1]), int(0.46 * img.shape[0])))

        Controller().async_click(self.roblox.hwnd, play_button)
        Controller().sync_click(self.roblox.hwnd, play_button)

        return True

    def get_game_status(self, img: np.ndarray) -> Tuple[bool]:
        # HELPER FUNCTION
        H, W, *_ = img.shape

        menu_cutout = img[69:99, W // 2]

        loaded_game = scv.has_color(menu_cutout, Colors.WHITE) and scv.has_color(menu_cutout, Colors.GRAY_1)
        loaded_select = .5 < np.count_nonzero(np.argmax(img, axis=2) == 1) / np.multiply(*img.shape[:2])

        return bool(loaded_select), bool(loaded_game)

    @ensure_n_times(n=5)
    def await_game(self, img: np.ndarray) -> bool:
        # WAIT TO LOAD INTO GAME
        return True in self.get_game_status(img)

    def navigate_game(self, img: np.ndarray) -> bool:
        H, W, *_ = img.shape

        loaded_select, loaded_game = self.get_game_status(img)

        if loaded_game or loaded_select:
            if loaded_select:
                # SELECT PRIOR
                time.sleep(.5)

                point = self.roblox.offset_point((round(W * 0.5 - H * 0.44), round(H * 0.77)))
                Controller().async_click(self.roblox.hwnd, point)
                Controller().sync_click(self.roblox.hwnd, point)

                time.sleep(2)

                point = self.roblox.offset_point((round(W * 0.5), round(H - 10)))
                Controller().async_click(self.roblox.hwnd, point)
                Controller().sync_click(self.roblox.hwnd, point)

                time.sleep(5)

            time.sleep(1)

            return True
        return False

    def open_data_menu(self, img: np.ndarray) -> bool:
        # OPEN DATA MENU
        H, W, *_ = img.shape

        Controller().sync_click(self.roblox.hwnd, self.roblox.offset_point((W // 2, 84)))

        time.sleep(1)

        Controller().sync_click(self.roblox.hwnd, self.roblox.offset_point((round(W * 0.5 - 67.67), 84)))

        time.sleep(1)

        return True

    @safe_execution
    @fail_n_times(n=5, step=-1)
    def get_data(self, img: np.ndarray) -> False | Type[Data]:
        data_output = {}
        data_format_iterator = iter(self.Data.FORMAT.items())

        # GET CONTOURS OF WINDOWS
        gray_mask = scv.mask_color(img, Colors.GRAY_1)

        data_contours = scv.find_contours(gray_mask)
        data_contours.sort(key=cv2.contourArea, reverse=True)

        data_contour, days_contour = data_contours[:2]

        data_img = scv.extract_contour(img, data_contour)
        subdata_img = data_img[:, int(data_img.shape[1] * 0.55):]

        # THERMOS
        for data_column in (subdata_img[:, :subdata_img.shape[1] // 2], subdata_img[:, subdata_img.shape[1] // 2:]):
            data_column[np.where(scv.mask_color(data_column, Colors.GRAY_1))] = 0

            data_mask = np.all(data_column != (0, 0, 0), axis=2).astype(np.uint8) * 255

            fields_contours = scv.find_contours(data_mask)
            fields_contours.sort(key=lambda e: scv.get_contour_center(e)[1])

            unit_coef_iterator = iter([
                0.7, # TEMPERATURE
                0.7, # DEW POINT
                2.75, # LAPSE RATE
                1.25, # HUMIDITY
                2.3, # CAPE
            ])

            for field_contour in fields_contours[1:6]:
                field_img = scv.extract_contour(data_column, field_contour)

                numbers_img = np.max(field_img, axis=2) - np.min(field_img, axis=2)
                numbers_img[np.where(numbers_img <= 8)] = 0

                numbers_img = scv.crop_image(numbers_img)
                numbers_img = numbers_img[:, :-round(next(unit_coef_iterator) * numbers_img.shape[0])]

                numbers_img = scv.spread_hist(numbers_img)
                numbers_img[np.where(numbers_img <= 8)] = 0

                numbers_img = scv.upscale(numbers_img, 8)
                numbers_img[np.where(numbers_img <= 140)] = 0

                scv.split_characters(numbers_img)

                characters_contours = scv.find_contours(numbers_img)
                characters_contours.sort(key=lambda e: scv.get_contour_center(e)[0], reverse=True)

                data_name, data_type = next(data_format_iterator)

                number = ""
                for character_contour in characters_contours:
                    character_img = scv.extract_contour(numbers_img, character_contour)

                    if character_img.shape[0] / numbers_img.shape[0] < 0.5:
                        if "." not in number and data_type == float:
                            number += "."
                        continue

                    result = ODRTwisted_1_19_1().detect(character_img)
                    number += str(result)

                data_output[data_name] = number[::-1]

        # DAYS
        days_img = scv.extract_contour(img, days_contour)
        days_mask = scv.mask_color(days_img, Colors.GRAY_0)
        days_contours = scv.find_contours(days_mask)
        days_contours.sort(key=lambda e: scv.get_contour_center(e)[0])

        for day_contour in days_contours[:3]:
            day_img = scv.extract_contour(days_img, day_contour)

            data_name, data_type = next(data_format_iterator)

            for day_type, color in Colors.DAYS.items():
                if scv.has_color(day_img, color):
                    data_output[data_name] = day_type
                    break

            else:
                data_output[data_name] = None

        full_data_mask = cv2.drawContours(np.zeros(img.shape[:2], np.uint8), [data_contour, days_contour], -1, 255, -1)

        data_trans = scv.crop_image(scv.mask_transparent(img, full_data_mask))

        return self.Data(**data_output), {"image": data_trans}
