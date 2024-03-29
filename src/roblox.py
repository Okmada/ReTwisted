import ctypes
import os
import threading
import time

import cv2
import numpy as np
import win32con
import win32gui
import win32ui

from ocr import Ocr

DESKTOP = win32gui.GetDesktopWindow()

class Roblox(threading.Thread):
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

    CLASS_NAMES = {
        "WINDOWSCLIENT": "Roblox Player",
        "ApplicationFrameWindow": "UWP Roblox"
    }

    PLACE_ID = 6161235818

    def __init__(self, name, controller, config, webhook):
        super().__init__(daemon=True)

        assert name in self.CLASS_NAMES, "Invalid roblox"

        self.name = name
        self.controller = controller
        self.config = config
        self.webhook = webhook

        self.pause_event = threading.Event()

        self._enabled = bool(self.config.get([self.name, "enabled"]) or False)
        self._lite_mode = bool(self.config.get([self.name, "litemode"]) or False)
        self._server = int(self.config.get([self.name, "server"]) or 0)

        self._data_callbacks = []
        self._pause_callbacks = []

        self.phase = 1
        self.hwnd = 0

        self.start()

    def run(self):
        while True:
            try:
                self.pause_event.wait()

                if self.is_timedout():
                    raise Exception("time for reroll exceeded limit (timeout)")

                if self.hwnd != 0 and self.is_crashed():
                    raise Exception("roblox crashed")

                img = self.get_screenshot()

                match self.phase:
                    case 1:
                        # START ROBLOX AND WAIT FOR HWND
                        self.start_roblox()

                        for _ in range(10):
                            if hwnd := self.find_roblox():
                                self.hwnd = hwnd
                                self.phase += 1
                                break
                            time.sleep(1)

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
                            self.controller.async_click(self.hwnd, lite_mode_button)

                        self.controller.async_click(self.hwnd, play_button)

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
                            self.controller.async_click(self.hwnd, (round(W * 0.5 + 3), round(H * 0.7 + 4)))
                            self.controller.sync_click(self.hwnd, (round(W * 0.5 + 3), round(H * 0.7 + 4)))

                            time.sleep(.5)

                            self.controller.async_click(self.hwnd, (round(W * 0.5 + 120), round(H * 0.4705 + 15)))
                            self.controller.sync_click(self.hwnd, (round(W * 0.5 + 120), round(H * 0.4705 + 15)))

                            time.sleep(1)

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
                            self.controller.async_click(self.hwnd, (84, 53))

                        # OPEN DATA MENU
                        H, W, *_ = img.shape
                        
                        self.controller.async_click(self.hwnd, (W//2, 95))

                        self.controller.sync_click(self.hwnd, (W//2 - 63, 95))

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
                            self.controller.sync_click(self.hwnd, (round(W * 0.6253), round(H * 0.4387 + 111)))
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

                        # PROCESS MAIN DATA
                        main_data = self._mask_image(data, data_masks[0])
                        main_data_mask = cv2.bitwise_xor(cv2.inRange(main_data, GRAY, GRAY), data_masks[0])
                        
                        main_data_contours, _ = cv2.findContours(main_data_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        main_data_contours = sorted(main_data_contours, key=lambda e: sum(self._get_contour_center(e)))

                        # default handling
                        for cont in (main_data_contours[i] for i in [0, 1, 2, 3, 4, 5, 6]):
                            cont_img = self._crop_contour(data, cont)
                            mins = cv2.merge([np.min(cont_img, axis=2)] * 3)

                            data_output.append(self._read_number(cont_img - mins))

                        # special handling for rhs
                        for cont in (main_data_contours[i] for i in [7, 8]):
                            cont_img = self._crop_contour(data, cont)
                            mins = cv2.merge([np.min(cont_img, axis=2)] * 3)

                            cont_img = self._crop_image(cont_img - mins)
                            cont_img = cont_img[:, :-round(cont_img.shape[0] * 1.2)]

                            data_output.append(self._read_number(cont_img))


                        # PROCESS DATA ON SIDE
                        side_data = self._mask_image(data, data_masks[1])
                        side_data_mask = cv2.bitwise_xor(cv2.inRange(side_data, GRAY, GRAY), data_masks[1])

                        side_data_contours, _ = cv2.findContours(side_data_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        side_data_contours = sorted(side_data_contours, key=lambda e: sum(self._get_contour_center(e)))

                        # special handling for srh
                        cont_img = self._crop_contour(data, side_data_contours[0])
                        mins = cv2.merge([np.min(cont_img, axis=2)] * 3)

                        cont_img = self._crop_image(cont_img - mins)
                        cont_img = cont_img[:, :round(cont_img.shape[1] * 0.45 - 1)]

                        data_output.append(self._read_number(cont_img))

                        # default handling
                        for cont in (side_data_contours[i] for i in [1, 3, 4]):
                            cont_img = self._crop_contour(data, cont)

                            data_output.append(self._read_number(cont_img))

                        # PROCESS DAYS DATA
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
                        data_formated = self.Data(*data_output)

                        print(self.get_name(), data_formated)

                        [f(data_formated) for f in self._data_callbacks]

                        if self.check_conditions(data_formated):
                            print(self.get_name(), "Conditions passed")

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
                print(self.get_name(), repr(e))

                self.time = time.time()
                self.phase = 1
                self.hwnd = 0
            

    def start_roblox(self):
        arg = f"roblox://placeId={self.PLACE_ID}" + (f"&linkCode={self._server}" if self._server else "")

        match self.name:
            case "WINDOWSCLIENT":
                for root, dirs, files in os.walk(
                        os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs")):
                    if (file := 'Roblox Player.lnk') in files:
                        path = os.path.join(root, file)
                        break

                else:
                    raise Exception("Roblox player is not installed")

                os.startfile(path, arguments=arg)
            case "ApplicationFrameWindow":
                os.startfile(arg)
            case _:
                return None

    def find_roblox(self):
        return win32gui.FindWindow(self.name, "Roblox")
    
    def close_roblox(self):
        win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)

    def is_timedout(self):
        time_max = int(self.config.get(["config", "timeout"]) or 0)

        return time.time() - self.time > time_max if time_max else False

    def is_crashed(self):
        if self.name == "WINDOWSCLIENT":
            if (win := win32gui.FindWindow(None, "Roblox Crash")) != 0:
                win32gui.PostMessage(win, win32con.WM_CLOSE, 0, 0)
                return True

        return not win32gui.IsWindow(self.hwnd)

    def get_screenshot(self):
        if not win32gui.IsWindow(self.hwnd):
            return None
        
        scaleFactor = ctypes.windll.user32.GetDpiForWindow(self.hwnd) / 96.0

        left, top, right, bot = win32gui.GetWindowRect(self.hwnd)
        unscaled_w, unscaled_h = right - left, bot - top
        scaled_w, scaled_h = round(unscaled_w * scaleFactor), round(unscaled_h * scaleFactor)

        for _ in range(3):
            try:
                hwndDC = win32gui.GetWindowDC(self.hwnd)
                mfcDC = win32ui.CreateDCFromHandle(hwndDC)
                saveDC = mfcDC.CreateCompatibleDC()

                saveBitMap = win32ui.CreateBitmap()
                saveBitMap.CreateCompatibleBitmap(mfcDC, scaled_w, scaled_h)
                saveDC.SelectObject(saveBitMap)

                match self.name:
                    case "WINDOWSCLIENT":
                        saveDC.BitBlt((0, 0), (scaled_w, scaled_h), mfcDC, (0, 0), win32con.SRCCOPY)
                    case "ApplicationFrameWindow":
                        ctypes.windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 2)
                    case _:
                        return None

                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)

                # win32gui.ReleaseDC(self.hwnd, hwndDC)
                mfcDC.DeleteDC()
                saveDC.DeleteDC()
                win32gui.DeleteObject(saveBitMap.GetHandle())
            except:
                continue
            break
        else:
            raise Exception("could not grab screenshot, crash?")

        img = np.frombuffer(bmpstr, dtype=np.uint8)
        img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
        img = img[:, :, :3]

        img = cv2.resize(img, (unscaled_w, unscaled_h), interpolation=cv2.INTER_NEAREST)

        return img.astype(dtype=np.uint8)

    def pause(self):
        self.pause_event.clear()

    def unpause(self):
        if self._enabled:
            self.time = time.time()

            self.pause_event.set()

    def set_enabled(self, value):
        value = bool(value)

        self._enabled = value
        self.config.set([self.name, "enabled"], value)

    def set_lite_mode(self, value):
        value = bool(value)

        self._lite_mode = value
        self.config.set([self.name, "litemode"], value)

    def set_server(self, value):
        value = int(value) if value else 0

        self._server = value
        self.config.set([self.name, "server"], value)

    def get_enabled(self):
        return self._enabled

    def get_lite_mode(self):
        return self._lite_mode

    def get_server(self):
        return self._server

    def get_name(self):
        return self.CLASS_NAMES[self.name]

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

    def add_data_callback(self, func):
        self._data_callbacks.append(func)

    def add_pause_callback(self, func):
        self._pause_callbacks.append(func)

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
    def _preprocess_for_ocr(image):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        mask = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        image = np.where(mask, image, 0)

        image = (image * (255 / np.max(image))).astype(np.uint8)

        image = Roblox._crop_image(image)

        SCALE = 120 / image.shape[0]
        new_dims = [round(dim * SCALE) for dim in image.shape[:2]][::-1]

        image = cv2.resize(image, new_dims, interpolation=cv2.INTER_LINEAR)

        BORDER = 20
        image = cv2.copyMakeBorder(image, BORDER, BORDER, BORDER, BORDER, cv2.BORDER_CONSTANT)

        return image

    @staticmethod
    def _read_number(image):
        image = Roblox._preprocess_for_ocr(image)

        text = Ocr.ocr(image)

        text = "".join([c for c in text if c in "0123456789."])
        text = ".".join([e for e in text.split(".") if len(e)][:2])
        return text or "0"

    @staticmethod
    def _mask_image(image, mask):
        return cv2.bitwise_and(image, image, mask=mask)

    @staticmethod
    def _crop_contour(image, contour):
        x, y, w, h = cv2.boundingRect(contour)
        return image[y:y+h, x:x+w]
