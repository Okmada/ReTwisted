import ctypes
import os
import time

import cv2
import numpy as np

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

WM_CLOSE = 0x10

SRCCOPY = 0xCC0020

class BitmapInfoHeader(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_ulong),
                ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long),
                ("biPlanes", ctypes.c_ushort),
                ("biBitCount", ctypes.c_ushort),
                ("biCompression", ctypes.c_ulong),
                ("biSizeImage", ctypes.c_ulong),
                ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", ctypes.c_ulong),
                ("biClrImportant", ctypes.c_ulong)]

class RGBQuad(ctypes.Structure):
    _fields_ = [("rgbBlue", ctypes.c_byte),
                ("rgbGreen", ctypes.c_byte),
                ("rgbRed", ctypes.c_byte),
                ("rgbReserved", ctypes.c_byte)]

class BitmapInfo(ctypes.Structure):
    _fields_ = [("bmiHeader", BitmapInfoHeader),
                ("bmiColors", RGBQuad)]

def get_window_rect(hwnd):
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom

class Roblox:
    CLASS_NAMES = {
        "WINDOWSCLIENT": "Roblox Player",
        "ApplicationFrameWindow": "UWP Roblox"
    }

    def __init__(self, name):
        assert name in self.CLASS_NAMES, "Invalid roblox"

        self._name = name
        self._hwnd = 0
            
    def start_roblox(self, place_id, server=""):
        arg = f"roblox://placeId={place_id}" + (f"&linkCode={server}" if server else "")

        match self._name:
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
            
        self.find_roblox()

    def find_roblox(self, retries=20):
        for _ in range(retries):
            if hwnd := user32.FindWindowW(self._name, "Roblox"):
                self._hwnd = hwnd
                break
            time.sleep(1)
        else:
            raise Exception("Could not find roblox")

    def close_roblox(self):
        user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)

    def is_crashed(self):
        if self._hwnd == 0:
            return False
        
        if self._name == "WINDOWSCLIENT":
            if win := user32.FindWindowW(None, "Roblox Crash"):
                user32.PostMessageW(win, WM_CLOSE, 0, 0)
                self._hwnd = 0
                return True

        if not user32.IsWindow(self._hwnd):
            self._hwnd = 0
            return True
        else:
            return False
    
    def get_screenshot(self):
        if not user32.IsWindow(self._hwnd):
            return None

        scaleFactor = user32.GetDpiForWindow(self._hwnd) / 96.0

        left, top, right, bot = get_window_rect(self._hwnd)
        unscaled_w, unscaled_h = right - left, bot - top
        scaled_w, scaled_h = round(unscaled_w * scaleFactor), round(unscaled_h * scaleFactor)

        hwndDC = user32.GetWindowDC(self._hwnd)
        mfcDC = gdi32.CreateCompatibleDC(hwndDC)

        saveBitMap = gdi32.CreateCompatibleBitmap(hwndDC, scaled_w, scaled_h)
        gdi32.SelectObject(mfcDC, saveBitMap)

        match self._name:
            case "WINDOWSCLIENT":
                gdi32.BitBlt(mfcDC, 0, 0, scaled_w, scaled_h, hwndDC, 0, 0, SRCCOPY)
            case "ApplicationFrameWindow":
                user32.PrintWindow(self._hwnd, mfcDC, 2)
            case _:
                return None

        bmpinfo = BitmapInfo()
        bmpinfo.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
        bmpinfo.bmiHeader.biWidth = scaled_w
        bmpinfo.bmiHeader.biHeight = -scaled_h
        bmpinfo.bmiHeader.biPlanes = 1
        bmpinfo.bmiHeader.biBitCount = 32
        bmpinfo.bmiHeader.biCompression = 0

        bmpstr = ctypes.create_string_buffer(scaled_w * scaled_h * 4)
        gdi32.GetDIBits(mfcDC, saveBitMap, 0, scaled_h, bmpstr, ctypes.byref(bmpinfo), 0)

        gdi32.DeleteObject(saveBitMap)
        gdi32.DeleteDC(mfcDC)
        user32.ReleaseDC(self._hwnd, hwndDC)

        img = np.frombuffer(bmpstr.raw, dtype=np.uint8)
        img.shape = (scaled_h, scaled_w, 4)
        img = img[:, :, :3]

        img = cv2.resize(img, (unscaled_w, unscaled_h), interpolation=cv2.INTER_NEAREST)

        return img.astype(dtype=np.uint8)
    
    def get_name(self):
        return self.CLASS_NAMES[self._name]

    @property
    def name(self):
        return self._name

    @property
    def hwnd(self):
        return self._hwnd