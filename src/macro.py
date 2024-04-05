import re
import threading
import time

import cv2
import numpy as np

from ocr import Ocr

PLACE_ID = 6161235818

class Data:
    FORMAT = {
        "TEMPERATURE": int,
        "DEWPOINT": int,
        "CAPE": int,
        "3CAPE": int,
        "0-3KM LAPSE RATES": float,
        "3-6KM LAPSE RATES": float,
        "PWAT": float,
        "700-500mb RH": int,
        "SURFACE RH": int,

        "SRH": int,
        "STORM MOTION": int,
        "STP": int,
        "VTP": int,

        "DAY 1": str,
        "DAY 2": str,
        "DAY 3": str,
    }

    @staticmethod
    def _to_data_type(value, data_type):
        if data_type == int:
            value = "".join([ch for ch in value if ch in "0123456789"])
        elif data_type == float:
            value = "".join([ch for ch in value if ch in ".0123456789"])
        return data_type(value)

    def __new__(cls, *data) -> None:
        assert len(data) == len(cls.FORMAT)

        return {name: cls._to_data_type(value, data_type) 
                for (name, data_type), value 
                in zip(cls.FORMAT.items(), data, strict=True)}

class Macro(threading.Thread):
    def __init__(self, roblox, controller, config, webhook):
        super().__init__(daemon=True)

        self.pause_event = threading.Event()

        self.roblox = roblox
        self.controller = controller
        self.config = config
        self.webhook = webhook

        self.phase = 1
        self.time = None

        self._data_callbacks = []
        self._pause_callbacks = []

        self._enabled = bool(self.config.get([self.roblox.name, "enabled"]) or False)
        self._lite_mode = bool(self.config.get([self.roblox.name, "litemode"]) or False)
        self._server = int(self.config.get([self.roblox.name, "server"]) or 0)

        self.start()

    def run(self):
        while True:
            try:
                self.pause_event.wait()

                if self.is_timedout():
                    raise Exception("Time for reroll exceeded limit (timeout)")

                if self.roblox.is_crashed():
                    raise Exception("Roblox crashed")

                img = self.roblox.get_screenshot()

                match self.phase:
                    case 1:
                        # START ROBLOX AND WAIT FOR HWND
                        self.roblox.start_roblox(PLACE_ID, self._server)

                        self.phase += 1

                    case 2:
                        # WAIT FOR TWISTED TO LOAD INTO MENU
                        GREEN = np.array([127, 255, 170])
                        RED = np.array([127, 85, 255])

                        loaded = cv2.inRange(img, GREEN, GREEN).any() and cv2.inRange(img, RED, RED).any()
                        if loaded:
                            time.sleep(1)
                            self.phase += 1
                        
                    case 3:
                        # NAVIGATE MENU
                        slice = img[:, :int(0.22 * img.shape[1])]

                        GREEN = np.array([127, 255, 170])
                        RED = np.array([127, 85, 255])

                        green_mask = cv2.inRange(slice, GREEN, GREEN)
                        red_mask = cv2.inRange(slice, RED, RED)

                        green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        red_contours, _ = cv2.findContours(red_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

                        green_contour = max(green_contours, key=cv2.contourArea)
                        red_contour = sorted(red_contours, key=cv2.contourArea, reverse=True)[2]

                        play_button = self._get_contour_center(green_contour)
                        lite_mode_button = self._get_contour_center(red_contour)

                        if self._lite_mode:
                            self.controller.async_click(self.roblox.hwnd, lite_mode_button)

                        self.controller.async_click(self.roblox.hwnd, play_button)

                        self.phase += 1

                    case 4:
                        # WAIT TO LOAD INTO GAME
                        GRAY = np.array([25]*3)

                        H, W, *_ = img.shape
                        slice = img[round(H*0.96-3):round(H*0.96+3), round(W*0.962-3):round(W*0.962+3)]

                        loaded = not cv2.inRange(slice, GRAY, GRAY).all()
                        if loaded:
                            time.sleep(1.5)
                            self.phase += 1

                    case 5:
                        # SELECT PRIOR IF GRAY NOT DETECTED
                        if not cv2.inRange(img, GRAY, GRAY).any():
                            point = (round(W * 0.5 + 3), round(H * 0.7 + 4))
                            self.controller.async_click(self.roblox.hwnd, point)
                            self.controller.sync_click(self.roblox.hwnd, point)

                            time.sleep(.5)

                            point = (round(W * 0.51 + 120), round(H * 0.4705 + 15))
                            self.controller.async_click(self.roblox.hwnd, point)
                            self.controller.sync_click(self.roblox.hwnd, point)

                            time.sleep(3)

                        self.phase += 1

                    case 6:
                        # CLOSE CHAT
                        GRAY = np.array([50]*3)
                        WHITE = np.array([255]*3)

                        chat_slice = img[33:73, 64:104]
                        chat_contours, _ = cv2.findContours(cv2.inRange(chat_slice, GRAY, GRAY), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        chat_contours = sorted(chat_contours, key=cv2.contourArea)

                        chat_slice_mask = cv2.drawContours(np.zeros(chat_slice.shape[:2], np.uint8), [chat_contours[0]], -1, 255, -1)
                        chat_mask = cv2.inRange(chat_slice, WHITE, WHITE)
                        
                        if np.count_nonzero(cv2.bitwise_and(chat_slice_mask, chat_mask)) / np.count_nonzero(chat_slice_mask) > .25:
                            self.controller.async_click(self.roblox.hwnd, (84, 53))

                        # OPEN DATA MENU
                        H, W, *_ = img.shape
                        
                        self.controller.async_click(self.roblox.hwnd, (W//2, 95))

                        self.controller.sync_click(self.roblox.hwnd, (W//2 - 63, 95))

                        time.sleep(1)

                        self.phase += 1

                    case n if n in [7, 8]:
                        # CROP TO DATA WINDOW
                        H, W, *_ = img.shape

                        slice = img[129:round(0.465 * H + 120), round(0.28 * W):round(0.72 * W)]

                        # MASK DATA WINDOW
                        GRAY = np.array([50]*3)

                        gray_contours, _ = cv2.findContours(cv2.inRange(slice, GRAY, GRAY), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        gray_contours = sorted(gray_contours, key=cv2.contourArea, reverse=True)[:3]

                        if n == 7:
                            # COPY DATA and create individual masks
                            data = slice.copy()
                            data_mask = cv2.drawContours(np.zeros(slice.shape[:2], np.uint8), gray_contours, -1, 255, -1)
                            data_masks = [cv2.drawContours(np.zeros(slice.shape[:2], np.uint8), [c], -1, 255, -1) for c in gray_contours]

                            # MASK AND COPY CODE
                            code = img[33:81, 108:round(0.0646 * W + 114)].copy()
                            code_contours, _ = cv2.findContours(cv2.inRange(code, GRAY, GRAY), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            code_contours = sorted(code_contours, key=cv2.contourArea, reverse=True)[:1]

                            code_mask = np.zeros(code.shape[:2], np.uint8)
                            cv2.drawContours(code_mask, code_contours, -1, 255, -1)

                            # CLICK HODO BUTTON
                            self.controller.sync_click(self.roblox.hwnd, (round(W * 0.6253), round(H * 0.4387 + 111)))
                            time.sleep(.75)

                        elif n == 8:
                            # COPY HODO IMAGE
                            hodograph = slice.copy()

                            hodograph_mask = np.zeros(slice.shape[:2], np.uint8)
                            cv2.drawContours(hodograph_mask, [gray_contours[1]], -1, 255, -1)

                        self.phase += 1

                    case 9:
                        GRAY = np.array([50]*3)

                        data_output = []

                        # THERMOS
                        main_data = self._mask_image(data, data_masks[0])
                        main_data_mask = cv2.bitwise_xor(cv2.inRange(main_data, GRAY, GRAY), data_masks[0])
                        
                        main_data_contours, _ = cv2.findContours(main_data_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        main_data_contours = sorted(main_data_contours, key=lambda e: sum(self._get_contour_center(e)))

                        side_data = self._mask_image(data, data_masks[1])
                        side_data_mask = cv2.bitwise_xor(cv2.inRange(side_data, GRAY, GRAY), data_masks[1])

                        side_data_contours, _ = cv2.findContours(side_data_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        side_data_contours = sorted(side_data_contours, key=lambda e: sum(self._get_contour_center(e)))

                        CUT_COEFF = [
                            0.7, # TEMPERATURE
                            0.7,  # DEWPOINT
                            2, # CAPE
                            2, # 3CAPE
                            2.6, # 0-3KM LAPSES RATES
                            2.6, # 3-6KM LAPSES RATES
                            1.5, # PWAT
                            1.2, # 700-500mb RH
                            1.2, # SURFACE RH

                            2.5, # SRH
                            0, # STORM MOTION
                            0, # STP
                            0, # VTP
                        ]

                        for cont, unit_coef in zip(main_data_contours + [side_data_contours[i] for i in [0, 1, 3, 4]], CUT_COEFF, strict=True):
                            cont_img = self._crop_contour(data, cont)

                            cont_img = cv2.cvtColor(cont_img, cv2.COLOR_BGR2GRAY)

                            mask = cv2.threshold(cont_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                            cont_img = np.where(mask, cont_img, 0)

                            cont_img = (cont_img * (255 / np.max(cont_img))).astype(np.uint8)

                            cont_img = self._crop_image(cont_img)

                            if unit_coef:
                                cont_img = cont_img[:, :-round(unit_coef * cont_img.shape[0])]

                            SCALE = 340 / cont_img.shape[0]

                            cont_img = cv2.copyMakeBorder(cont_img, *[int(cont_img.shape[0] * 0.35)] * 4, cv2.BORDER_CONSTANT)
                            new_dims = [round(dim * SCALE) for dim in cont_img.shape[:2]][::-1]
                            cont_img = cv2.resize(cont_img, new_dims, interpolation=cv2.INTER_LINEAR)

                            data_output.append(self._read_number(cont_img))

                        # DAYS
                        top_data = self._mask_image(data, data_masks[2])
                        top_data_mask = cv2.bitwise_xor(cv2.inRange(top_data, GRAY, GRAY), data_masks[2])

                        top_data_contours, _ = cv2.findContours(top_data_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        top_data_contours = sorted(top_data_contours, key=lambda e: sum(self._get_contour_center(e)))

                        COLORS = {
                            (255, 127, 255): "HIGH",
                            (127, 197, 127): "MRGL",
                            (127, 246, 246): "SLGT",
                            (192, 232, 192): "TSTM",
                            (127, 127, 230): "MDT",
                            (127, 194, 230): "ENH"
                        }

                        for cont in top_data_contours[:3]:
                            cont_img = self._crop_contour(data, cont)

                            for color, value in COLORS.items():
                                if np.count_nonzero(cv2.inRange(cont_img, color, color)):
                                    data_output.append(value)
                                    break

                            else:
                                data_output.append(None)

                        # FORMAT DATA
                        data_formated = Data(*data_output)

                        print(self.roblox.get_name(), data_formated)

                        [f(data_formated) for f in self._data_callbacks]

                        if self.check_conditions(data_formated):
                            print(self.roblox.get_name(), "Conditions passed")

                            code_trans = self._crop_image(self._mask_transparent(code, code_mask))

                            data_trans = self._crop_image(self._mask_transparent(data, data_mask))
                            
                            hodograph_trans = self._crop_image(self._mask_transparent(hodograph, hodograph_mask))
                            hodograph_trans = np.concatenate((np.zeros([data_trans.shape[0] - hodograph_trans.shape[0], hodograph_trans.shape[1], 4]), hodograph_trans), axis=0)

                            joined_image = np.concatenate((data_trans, np.zeros((data_trans.shape[0], 10, 4)), hodograph_trans), axis=1)

                            self.webhook.send(data=data_formated, code_image=code_trans, data_image=joined_image)

                            [f() for f in self._pause_callbacks]

                        self.time = time.time()
                        self.phase = 1
            except Exception as e:
                print(self.roblox.get_name(), repr(e))

                self.time = time.time()
                self.phase = 1

    def pause(self):
        self.pause_event.clear()

    def unpause(self):
        if self._enabled:
            self.time = time.time()

            self.pause_event.set()

    def is_timedout(self):
        time_max = int(self.config.get(["config", "timeout"]) or 0)

        if not time_max:
            return False
        
        return time.time() - self.time > time_max if time_max else False

    def set_enabled(self, value):
        value = bool(value or False)

        self._enabled = value
        self.config.set([self.roblox.name, "enabled"], value)

    def set_lite_mode(self, value):
        value = bool(value or False)

        self._lite_mode = value
        self.config.set([self.roblox.name, "litemode"], value)

    def set_server(self, value):
        value = int(value or 0)

        self._server = value
        self.config.set([self.roblox.name, "server"], value)

    def get_enabled(self):
        return self._enabled

    def get_lite_mode(self):
        return self._lite_mode

    def get_server(self):
        return self._server

    def add_data_callback(self, func):
        self._data_callbacks.append(func)

    def add_pause_callback(self, func):
        self._pause_callbacks.append(func)

    def check_conditions(self, data):
        for group in self.config.get(["conditions"]) or []:
            for condition in group:
                what, comparision_type, expected_data = condition

                real_data = data[what]
                expected_data = type(real_data)(expected_data)

                if comparision_type == "==" and real_data != expected_data:
                    break
                elif comparision_type == ">=" and real_data < expected_data:
                    break
                elif comparision_type == "<=" and real_data > expected_data:
                    break
            else:
                return True
        return False

    @staticmethod
    def _get_contour_center(contour):
        M = cv2.moments(contour)
        center_X = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
        center_Y = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0
        return (center_X, center_Y)

    @staticmethod
    def _crop_image(image):
        non_empty_columns = np.where(image.max(axis=0)>0)[0]
        non_empty_rows = np.where(image.max(axis=1)>0)[0]

        cropBox = (min(non_empty_rows), max(non_empty_rows), min(non_empty_columns), max(non_empty_columns))
        return image[cropBox[0]:cropBox[1]+1, cropBox[2]:cropBox[3]+1]

    @staticmethod
    def _mask_transparent(image, mask):
        assert mask.shape[:2] == image.shape[:2], "missmatched mask shape"

        transparent_image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        transparent_image[mask == 0] = [0]*4

        return transparent_image

    @staticmethod
    def _read_number(image):
        text = Ocr.ocr(image)

        nums = re.findall("([0-9]+[.]{1}[0-9]+|[0-9]+)", text)

        return nums[-1] if nums else "0"

    @staticmethod
    def _mask_image(image, mask):
        return cv2.bitwise_and(image, image, mask=mask)

    @staticmethod
    def _crop_contour(image, contour):
        x, y, w, h = cv2.boundingRect(contour)
        return image[y:y+h, x:x+w]
