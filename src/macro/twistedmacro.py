import logging
import re
import time
from typing import Tuple, Type

import cv2
import numpy as np

from data import Data
from macro.macro import Macro
from ocr import Ocr

PLACE_ID = 6161235818

class Colors:
    WHITE = (255, 255, 255)
    GREEN = (127, 255, 170)

    GRAY_BUTTON = (79, 67, 64)

    GRAY_0 = (27, 23, 22)
    GRAY_1 = (34, 31, 28)
    GRAY_2 = (45, 38, 37)

    GRAYS = (GRAY_0, GRAY_1, GRAY_2)

    DAYS = {
        "HIGH": ((255, 127, 255), (200, 102, 198), (146, 79, 142)),
        "MRGL": ((160, 214, 6), (128, 167, 10), (98, 122, 17)),
        "SLGT": ((64, 198, 255), (56, 155, 198), (50, 114, 142)),
        "TSTM": ((192, 232, 192), (153, 181, 151), (114, 131, 110)),
        "MDT": ((79, 50, 186), (67, 44, 146), (58, 40, 107)),
        "ENH": ((83, 146, 249), (70, 116, 193), (60, 88, 139)),
    }

class TwistedData(Data):
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

class TwistedMacro(Macro):
    @property
    def steps(self):
        return[
            self.start_roblox,
            self.await_menu,
            self.navigate_menu,
            self.await_game,
            self.open_data_menu,
            self.get_data,
        ]

    def start_roblox(self, img: np.ndarray) -> bool:
        # START ROBLOX AND WAIT FOR HWND
        self.roblox.start_roblox(PLACE_ID, self.config.get([self.roblox.name, "server"]))

        return True

    def await_menu(self, img: np.ndarray) -> bool:
        # WAIT FOR TWISTED TO LOAD INTO MENU
        if np.all(img == Colors.GREEN, axis=2).any():
            time.sleep(1)
            return True
        return False

    def navigate_menu(self, img: np.ndarray) -> bool:
        # NAVIGATE MENU
        cutout = img[:, :int(0.22 * img.shape[1])]

        green_mask = np.all(cutout == Colors.GREEN, axis=2).astype(np.uint8) * 255

        green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        green_contour = max(green_contours, key=cv2.contourArea)

        play_button = self._get_contour_center(green_contour)

        self.controller.async_click(self.roblox.hwnd, play_button)

        time.sleep(3)

        return True

    def await_game(self, img: np.ndarray) -> bool:
        # WAIT TO LOAD INTO GAME
        H, W, *_ = img.shape

        rect_cutout = img[:, W//2 - min(H, W)//2:W//2 + min(H, W)//2]

        loaded_game = np.all(img[80:100, W - 44] == Colors.GRAY_BUTTON, axis=1).any()
        loaded_select = .5 < np.count_nonzero(np.argmax(rect_cutout, axis=2) == 1) / np.multiply(*rect_cutout.shape[:2])

        if loaded_game or loaded_select:
            logging.debug(f"{loaded_game=}")
            logging.debug(f"{loaded_select=}")

            if loaded_select:
                # SELECT PRIOR
                time.sleep(.5)

                point = (round(W * 0.5 + 3), round(H * 0.69 + 3))
                self.controller.async_click(self.roblox.hwnd, point)
                self.controller.sync_click(self.roblox.hwnd, point)

                time.sleep(1)

                point = (round(W * 0.5 + H * 0.12 + 3), round(H * 0.45 + 10))
                self.controller.async_click(self.roblox.hwnd, point)
                self.controller.sync_click(self.roblox.hwnd, point)

                time.sleep(5)

            time.sleep(1)

            return True
        return False

    def open_data_menu(self, img: np.ndarray) -> bool:
        # CLOSE CHAT
        chat_slice = img[50:80, 130:163]
        ratio = np.count_nonzero(np.all(chat_slice == Colors.WHITE, axis=2)) / np.multiply(*chat_slice.shape[:2])

        if ratio > .30:
            self.controller.sync_click(self.roblox.hwnd, (146, 65))

        # OPEN DATA MENU
        H, W, *_ = img.shape

        point = (round(W * 0.49374 - 67.67), 118)

        self.controller.sync_click(self.roblox.hwnd, point)

        time.sleep(1)

        return True

    def get_data(self, img: np.ndarray) -> False | Type[Data]:
        data_output = []

        # GET CONTOURS OF WINDOWS
        grays_mask = np.logical_or.reduce([np.all(img == gray, axis=2) for gray in Colors.GRAYS]).astype(np.uint8) * 255

        color_contours, _ = cv2.findContours(grays_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        color_contours = max(color_contours, key=cv2.contourArea)

        data_mask = cv2.drawContours(np.zeros(img.shape[:2], np.uint8), [color_contours], -1, 255, -1)

        sub_data_masks = np.bitwise_and(data_mask, np.all(img!=Colors.GRAY_2, axis=2)).astype(np.uint8) * 255
        sub_data_contours, _ = cv2.findContours(sub_data_masks, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        sub_data_contours = sorted(sub_data_contours, key=cv2.contourArea, reverse=True)

        sub_data_contours, composites_contour, days_contours = sub_data_contours[:3], sub_data_contours[4], sub_data_contours[5:8]

        sub_data_contours.sort(key=lambda e: self._get_contour_center(e)[0])
        days_contours.sort(key=lambda e: self._get_contour_center(e)[0])

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
            color_mask = cv2.bitwise_and(np.all(img == Colors.GRAY_0, axis=2).astype(np.uint8) * 255, contour_mask)

            color_contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color_contour = max(color_contours, key=cv2.contourArea)
            filled_color_mask = cv2.drawContours(np.zeros(color_mask.shape[:2], np.uint8), [color_contour], -1, 255, -1)

            text_mask = cv2.bitwise_and(filled_color_mask, cv2.bitwise_not(color_mask))

            rows_mask = np.zeros(text_mask.shape[:2], np.uint8)
            rows_mask[np.where(text_mask.max(axis=1)>0)[0]] = 255
            rows_mask = cv2.bitwise_and(filled_color_mask, rows_mask)

            rows_contours, _ = cv2.findContours(rows_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for row_contour in sorted(rows_contours, key=lambda e: self._get_contour_center(e)[1]):
                cont_img = self._extract_contour(img, row_contour)
                cont_img[np.where(np.all(cont_img == Colors.GRAY_0, axis=2))] = [0]

                color_text_mins = np.min(cont_img, axis=2)

                cont_img = cv2.cvtColor(cont_img, cv2.COLOR_BGR2GRAY)

                color_text = cont_img - color_text_mins
                color_text = (color_text * (255 / np.max(color_text))).astype(np.uint8)
                color_text[np.where(color_text <= 8)] = 0

                cont_img[np.where(color_text)] = 0
                cont_img[np.where(cont_img <= 32)] = 0
                cont_img = self._remove_dots(cont_img)
                cont_img = self._crop_image(cont_img, top=False, bottom=False)

                color_text = self._crop_image(color_text, top=False, bottom=False)
                color_text = color_text[:, :-round(next(unit_coef_iterator) * color_text.shape[0])]

                merged_img = np.concatenate([cont_img,
                                                np.zeros([cont_img.shape[0]]*2, np.uint8),
                                                color_text], axis=1)
                merged_img = self._upscale_for_ocr(merged_img)

                number = self._read_number(merged_img)
                data_output.append(number)

        # COMPOSITES
        composites = self._extract_contour(img, composites_contour)
        composites[np.where(np.all(composites == Colors.GRAY_0, axis=2))] = [0]

        composites = cv2.cvtColor(composites, cv2.COLOR_BGR2GRAY)
        composites[np.where(composites < 40)] = 0

        stp_img = self._crop_image(composites[:, :composites.shape[1]//2])
        vtp_img = self._crop_image(composites[:, composites.shape[1]//2:])

        stp_img = self._remove_dots(stp_img)
        vtp_img = self._remove_dots(vtp_img)

        stp_img = self._upscale_for_ocr(stp_img)
        vtp_img = self._upscale_for_ocr(vtp_img)

        data_output.append(self._read_number(stp_img))
        data_output.append(self._read_number(vtp_img))

        # ANGLE STORM MOTION
        # hodo_img = self._extract_contour(img, sub_data_contours[2])

        # wind_mask = np.all(hodo_img == Colors.GRAY_0, axis=2).astype(np.uint8) * 255

        # wind_contours, _ = cv2.findContours(wind_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # wind_contours = [c for c in wind_contours if cv2.contourArea(c) > 10]

        # wind_img = self._extract_contour(hodo_img, cv2.convexHull(np.vstack(wind_contours)))

        # thresh_img = np.where(wind_img == 255, wind_img, 0)

        # rows_mask = np.zeros(thresh_img.shape[:2], np.uint8)
        # rows_mask[np.where(thresh_img.max(axis=1) > 0)[0]] = 255

        # rows_contours, _ = cv2.findContours(rows_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # for row_contour in sorted(rows_contours, key=lambda e: self._get_contour_center(e)[1]):
        #     row_img = self._extract_contour(wind_img, row_contour)
        #     row_img = cv2.cvtColor(row_img, cv2.COLOR_BGR2GRAY)

        #     row_img = np.where(row_img > 150, row_img, 0)

        #     row_img = self._remove_dots(row_img)
        #     row_img = self._crop_image(row_img)
        #     row_img = self._upscale_for_ocr(row_img)

        #     number = self._read_number(row_img)

        #     data_output.append(number)

        # DAYS
        for i, cont in enumerate(days_contours):
            cont_img = self._extract_contour(img, cont)

            for day_type, colors in Colors.DAYS.items():
                if np.all(cont_img == colors[i], axis=2).any():
                    data_output.append(day_type)
                    break

            else:
                data_output.append(None)

        code_row = img[40:90]
        code_row_mask = np.all(code_row == Colors.GRAY_2, axis=2).astype(np.uint8) * 255

        code_contour, _ = cv2.findContours(code_row_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        code_contour = min(code_contour, key=lambda e: self._get_contour_center(e)[0])

        code_mask = cv2.drawContours(np.zeros(code_row.shape[:2], np.uint8), [code_contour], -1, 255, -1)
        code_trans = self._crop_image(self._mask_transparent(code_row, code_mask))

        data_trans = self._crop_image(self._mask_transparent(img, data_mask))

        try:
            return TwistedData(*data_output), data_trans, code_trans
        except:
            return False

    @staticmethod
    def _get_contour_center(contour: np.ndarray) -> Tuple[int, int]:
        M = cv2.moments(contour)
        center_X = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
        center_Y = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0
        return (center_X, center_Y)

    @staticmethod
    def _crop_image(image: np.ndarray, top=True, bottom=True, left=True, right=True) -> np.ndarray:
        H, W, *_ = image.shape

        non_empty_columns = np.where(image.max(axis=0) > 0)[0]
        non_empty_rows = np.where(image.max(axis=1) > 0)[0]

        crop_box = (min(non_empty_rows) if top else 0,
                   max(non_empty_rows)+1 if bottom else H,
                   min(non_empty_columns) if left else 0,
                   max(non_empty_columns)+1 if right else W)
        return image[crop_box[0]:crop_box[1], crop_box[2]:crop_box[3]]

    @staticmethod
    def _mask_transparent(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        assert mask.shape[:2] == image.shape[:2], "missmatched mask shape"

        transparent_image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        transparent_image[mask == 0] = [0]*4

        return transparent_image

    @staticmethod
    def _upscale_for_ocr(image: np.ndarray) -> np.ndarray:
        scale = 325 / image.shape[0]

        image = cv2.copyMakeBorder(image, *[int(image.shape[0] * 0.35)] * 4, cv2.BORDER_CONSTANT)
        new_dims = [round(dim * scale) for dim in image.shape[:2]][::-1]
        image = cv2.resize(image, new_dims, interpolation=cv2.INTER_LINEAR)

        return image

    @staticmethod
    def _read_number(image: np.ndarray) -> str:
        text = Ocr.ocr(image)

        text = text.replace("Ø", "0")
        text = text.replace("ø", "0")
        text = text.replace("l", "1")

        nums = re.findall("([0-9]+[.]{1}[0-9]+|[0-9]+)", text)

        return nums[-1] if nums else "0"

    @staticmethod
    def _extract_contour(image: np.ndarray, contour: np.ndarray) -> np.ndarray:
        X, Y, W, H = cv2.boundingRect(contour)

        cutout = np.zeros([H, W] + list(image.shape[2:]), np.uint8)
        cv2.drawContours(cutout, [contour - [X, Y]], -1, [255]*3, -1)
        points = np.where(np.all(cutout, axis=2))

        cutout[points] = image[tuple(np.dstack((np.dstack(points) + [Y, X])[0])[0])]

        return cutout

    @staticmethod
    def _remove_dots(image: np.ndarray) -> np.ndarray:
        H, W, *_ = image.shape
        to_delete = []

        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for contour in contours:
            cont_x, cont_y, cont_w, cont_h = cv2.boundingRect(contour)

            if 0.5 > cont_h / H:
                to_delete += range(cont_x, cont_x + cont_w)

        return np.delete(image, to_delete, axis=1)