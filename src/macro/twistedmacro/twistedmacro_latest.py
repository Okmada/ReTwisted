import time
from typing import Tuple, Type

import cv2
import numpy as np

import simplecv as scv
from config import ConfigManager
from macro.macro import Macro, ensure_n_times, fail_n_times, safe_execution
from odr import ODR

PLACE_ID = "6161235818"

class Colors:
    GREEN = (127, 255, 170)

    GRAY_BUTTON = (79, 67, 64)

    GRAY_0 = (27, 23, 22)
    GRAY_1 = (45, 38, 37)

    DAYS = {
        "HIGH": ((255, 127, 255), (200, 102, 198), (146, 79, 142)),
        "MRGL": ((160, 214, 6), (128, 167, 10), (98, 122, 17)),
        "SLGT": ((64, 198, 255), (56, 155, 198), (50, 114, 142)),
        "TSTM": ((192, 232, 192), (153, 181, 151), (114, 131, 110)),
        "MDT": ((79, 50, 186), (67, 44, 146), (58, 40, 107)),
        "ENH": ((83, 146, 249), (70, 116, 193), (60, 88, 139)),
    }


class TwistedMacro_latest(Macro):
    class Data(Macro.Data):
        FORMAT = {
            "TEMPERATURE": int,
            "CAPE": int,
            "0-3KM LAPSE RATES": float,
            "PWAT": float,
            "SURFACE RH": int,

            "DEWPOINT": int,
            "3CAPE": int,
            "3-6KM LAPSE RATES": float,
            "SRH": int,
            "700-500mb RH": int,

            "STP": int,
            "VTP": int,

            # "ANGLE": int,
            # "STORM MOTION": int,

            "DAY 1": str,
            "DAY 2": str,
            "DAY 3": str,
        }

    @property
    def steps(self):
        return[
            self.start_roblox,
            self.await_menu,
            self.navigate_menu,
            self.await_game,
            self.navigate_game,
            self.open_data_menu,
            self.get_data,
        ]

    def start_roblox(self, img: np.ndarray) -> bool:
        # START ROBLOX AND WAIT FOR HWND
        server = ConfigManager().get(["roblox", self.roblox.name, "server"])
        self.roblox.join_place(PLACE_ID, server)

        return True

    @ensure_n_times(n=3, delay=.3)
    def await_menu(self, img: np.ndarray) -> bool:
        # WAIT FOR TWISTED TO LOAD INTO MENU
        cutout = img[:, :int(0.22 * img.shape[1])]

        return scv.has_color(cutout, Colors.GREEN)

    def navigate_menu(self, img: np.ndarray) -> bool:
        # NAVIGATE MENU
        cutout = img[:, :int(0.22 * img.shape[1])]

        green_mask = scv.mask_color(cutout, Colors.GREEN)

        green_contours = scv.find_contours(green_mask)

        green_contour = max(green_contours, key=cv2.contourArea)

        play_button = self.roblox.offset_point(scv.get_contour_center(green_contour))

        self.controller.async_click(self.roblox.hwnd, play_button)

        return True

    def get_game_status(self, img: np.ndarray) -> Tuple[bool]:
        # HELPER FUNCTION
        H, W, *_ = img.shape

        rect_cutout = img[:, W//2 - min(H, W)//2:W//2 + min(H, W)//2]

        loaded_game = scv.has_color(img[40:60, W - 35], Colors.GRAY_BUTTON)
        loaded_select = .5 < np.count_nonzero(np.argmax(rect_cutout, axis=2) == 1) / np.multiply(*rect_cutout.shape[:2])

        return bool(loaded_select), bool(loaded_game)

    @ensure_n_times(n=3, delay=.3)
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

                point = self.roblox.offset_point((round(W * 0.5 + 3), round(H * 0.69 + 3)))
                self.controller.async_click(self.roblox.hwnd, point)
                self.controller.sync_click(self.roblox.hwnd, point)

                time.sleep(1)

                point = self.roblox.offset_point((round(W * 0.5 + H * 0.12 + 3), round(H * 0.45 + 10)))
                self.controller.async_click(self.roblox.hwnd, point)
                self.controller.sync_click(self.roblox.hwnd, point)

                time.sleep(5)

            time.sleep(1)

            return True
        return False

    def open_data_menu(self, img: np.ndarray) -> bool:
        # CLOSE CHAT
        if self.roblox.is_chat_open():
            self.controller.sync_click(self.roblox.hwnd, self.roblox.get_chat_pos())

        # OPEN DATA MENU
        H, W, *_ = img.shape

        point = self.roblox.offset_point((round(W * 0.5 - 67.67), 85))

        self.controller.sync_click(self.roblox.hwnd, point)

        time.sleep(1)

        return True

    @safe_execution
    @fail_n_times(n=5, delay=.5, steps_return=-1)
    def get_data(self, img: np.ndarray) -> False | Type[Data]:
        data_output = []

        # GET CONTOURS OF WINDOWS
        gray_mask = scv.mask_color(img, Colors.GRAY_1)

        data_contours = scv.find_contours(gray_mask)
        data_contour = max(data_contours, key=cv2.contourArea)

        data_mask = cv2.drawContours(np.zeros(img.shape[:2], np.uint8), [data_contour], -1, 255, -1)

        sub_data_masks = np.bitwise_and(data_mask, np.bitwise_not(gray_mask)).astype(np.uint8) * 255
        sub_data_contours = scv.find_contours(sub_data_masks)
        sub_data_contours.sort(key=cv2.contourArea, reverse=True)

        sub_data_contours, composites_contour, days_contours = sub_data_contours[:3], sub_data_contours[3], sub_data_contours[4:7]

        sub_data_contours.sort(key=lambda e: scv.get_contour_center(e)[0])
        days_contours.sort(key=lambda e: scv.get_contour_center(e)[0])

        # THERMOS
        unit_coef_iterator = iter([
            0.7, # TEMPERATURE
            2.5, # CAPE
            2.6, # 0-3KM LAPSES RATES
            1.5, # PWAT
            0.7, # SURFACE RH

            0.7, # DEWPOINT
            2.5, # 3CAPE
            2.6, # 3-6KM LAPSES RATES
            3, # SRH
            0.7, # 700-500mb RH
        ])

        for contour in sub_data_contours[:2]:
            contour_mask = cv2.drawContours(np.zeros(img.shape[:2], np.uint8), [contour], -1, 255, -1)
            color_mask = cv2.bitwise_and(scv.mask_color(img, Colors.GRAY_0), contour_mask)

            color_contours = scv.find_contours(color_mask)
            color_contour = max(color_contours, key=cv2.contourArea)
            filled_color_mask = cv2.drawContours(np.zeros(color_mask.shape[:2], np.uint8), [color_contour], -1, 255, -1)

            text_mask = cv2.bitwise_and(filled_color_mask, cv2.bitwise_not(color_mask))

            rows_mask = np.zeros(text_mask.shape[:2], np.uint8)
            rows_mask[np.where(text_mask.max(axis=1)>0)[0]] = 255
            rows_mask = cv2.bitwise_and(filled_color_mask, rows_mask)

            rows_contours = scv.find_contours(rows_mask)
            rows_contours.sort(key=lambda e: scv.get_contour_center(e)[1])

            for row_contour in rows_contours:
                cont_img = scv.extract_contour(img, row_contour)
                cont_img[np.where(scv.mask_color(cont_img, Colors.GRAY_0))] = [0]

                color_text_mins = np.min(cont_img, axis=2)

                cont_img = cv2.cvtColor(cont_img, cv2.COLOR_BGR2GRAY)

                color_text = cont_img - color_text_mins

                color_text = scv.spread_hist(color_text)
                color_text[np.where(color_text <= 8)] = 0

                color_text = scv.crop_image(color_text, top=False, bottom=False)
                color_text = color_text[:, :-round(next(unit_coef_iterator) * color_text.shape[0])]

                color_text = scv.upscale(color_text, 16)
                color_text[np.where(color_text <= 140)] = 0

                scv.split_characters(color_text)

                characters_contours = scv.find_contours(color_text)
                characters_contours.sort(key=lambda e: scv.get_contour_center(e)[0], reverse=True)

                number = ""
                for character_contour in characters_contours:
                    character_img = scv.extract_contour(color_text, character_contour)

                    if character_img.shape[0] / color_text.shape[0] < 0.5:
                        if "." not in number:
                            number += "."
                        continue

                    result = ODR().detect(cv2.cvtColor(character_img, cv2.COLOR_GRAY2BGR))
                    number += str(result)

                data_output.append(number[::-1])

        # COMPOSITES
        composites = scv.extract_contour(img, composites_contour)
        composites[np.where(scv.mask_color(composites, Colors.GRAY_0))] = [0]

        composites = cv2.cvtColor(composites, cv2.COLOR_BGR2GRAY)
        composites[np.where(composites < 40)] = 0

        for composite in (composites[:, :composites.shape[1]//2], composites[:, composites.shape[1]//2:]):
            composite = scv.crop_image(composite)

            composite = scv.upscale(composite, 8)
            composite[np.where(composite <= 140)] = 0

            characters_contours = scv.find_contours(composite)
            characters_contours.sort(key=lambda e: scv.get_contour_center(e)[0], reverse=True)

            number = ""
            for character_contour in characters_contours:
                character_img = scv.extract_contour(composite, character_contour)

                if character_img.shape[0] / composite.shape[0] < 0.5:
                    break

                result = ODR().detect(cv2.cvtColor(character_img, cv2.COLOR_GRAY2BGR))
                number += str(result)

            data_output.append(number[::-1])

        # ANGLE STORM MOTION
        # hodo_img = scv.extract_contour(img, sub_data_contours[2])

        # wind_mask = np.all(hodo_img == Colors.GRAY_0, axis=2).astype(np.uint8) * 255

        # wind_contours = scv.find_contours(wind_mask)
        # wind_contours = [c for c in wind_contours if cv2.contourArea(c) > 10]

        # wind_img = scv.extract_contour(hodo_img, cv2.convexHull(np.vstack(wind_contours)))

        # thresh_img = np.where(wind_img == 255, wind_img, 0)

        # rows_mask = np.zeros(thresh_img.shape[:2], np.uint8)
        # rows_mask[np.where(thresh_img.max(axis=1) > 0)[0]] = 255

        # rows_contours = scv.find_contours(rows_mask)
        # rows_contours.sort(key=lambda e: scv.get_contour_center(e)[1])

        # for row_contour in rows_contours:
        #     row_img = scv.extract_contour(wind_img, row_contour)
        #     row_img = cv2.cvtColor(row_img, cv2.COLOR_BGR2GRAY)

        #     row_img = np.where(row_img > 150, row_img, 0)

        #     row_img = self._remove_dots(row_img)
        #     row_img = scv.crop_image(row_img)

        #     number = scv.read_number(row_img)

        #     data_output.append(number)

        # DAYS
        for i, cont in enumerate(days_contours):
            cont_img = scv.extract_contour(img, cont)

            for day_type, colors in Colors.DAYS.items():
                if scv.has_color(cont_img, colors[i]):
                    data_output.append(day_type)
                    break

            else:
                data_output.append(None)

        code_row = img[:60]
        code_row_mask = scv.mask_color(code_row, Colors.GRAY_1)

        code_contour = scv.find_contours(code_row_mask)
        code_contour = min(code_contour, key=lambda e: scv.get_contour_center(e)[0])

        code_mask = cv2.drawContours(np.zeros(code_row.shape[:2], np.uint8), [code_contour], -1, 255, -1)
        code_trans = scv.crop_image(scv.mask_transparent(code_row, code_mask))

        top_mask = np.bitwise_and(np.bitwise_not(data_mask), scv.mask_color(img, Colors.GRAY_0))
        top_contour = max(scv.find_contours(top_mask), key=cv2.contourArea)
        full_data_contour = cv2.convexHull(np.vstack((top_contour, data_contour)))
        full_data_mask = cv2.drawContours(np.zeros(img.shape[:2], np.uint8), [full_data_contour], -1, 255, -1)

        data_trans = scv.crop_image(scv.mask_transparent(img, full_data_mask))

        return self.Data(*data_output), data_trans, code_trans
