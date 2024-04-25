import ctypes
import os
import time

import cv2
import numpy as np
import win32con
import win32gui
import win32ui

DESKTOP = win32gui.GetDesktopWindow()

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
            if hwnd := win32gui.FindWindow(self._name, "Roblox"):
                self._hwnd = hwnd
                break
            time.sleep(1)
        else:
            raise Exception("Could not find roblox")
    
    def close_roblox(self):
        win32gui.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)

    def is_crashed(self):
        if self._hwnd == 0:
            return False
        
        if self._name == "WINDOWSCLIENT":
            if (win := win32gui.FindWindow(None, "Roblox Crash")) != 0:
                win32gui.PostMessage(win, win32con.WM_CLOSE, 0, 0)
                self._hwnd = 0
                return True

        if not win32gui.IsWindow(self._hwnd):
            self._hwnd = 0
            return True
        else:
            return False
    
    def get_screenshot(self):
        if not win32gui.IsWindow(self._hwnd):
            return None
        
        scaleFactor = ctypes.windll.user32.GetDpiForWindow(self._hwnd) / 96.0

        left, top, right, bot = win32gui.GetWindowRect(self._hwnd)
        unscaled_w, unscaled_h = right - left, bot - top
        scaled_w, scaled_h = round(unscaled_w * scaleFactor), round(unscaled_h * scaleFactor)

        for _ in range(3):
            try:
                hwndDC = win32gui.GetWindowDC(self._hwnd)
                mfcDC = win32ui.CreateDCFromHandle(hwndDC)
                saveDC = mfcDC.CreateCompatibleDC()

                saveBitMap = win32ui.CreateBitmap()
                saveBitMap.CreateCompatibleBitmap(mfcDC, scaled_w, scaled_h)
                saveDC.SelectObject(saveBitMap)

                match self._name:
                    case "WINDOWSCLIENT":
                        saveDC.BitBlt((0, 0), (scaled_w, scaled_h), mfcDC, (0, 0), win32con.SRCCOPY)
                    case "ApplicationFrameWindow":
                        ctypes.windll.user32.PrintWindow(self._hwnd, saveDC.GetSafeHdc(), 2)
                    case _:
                        return None

                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)

                # win32gui.ReleaseDC(self._hwnd, hwndDC)
                mfcDC.DeleteDC()
                saveDC.DeleteDC()
                win32gui.DeleteObject(saveBitMap.GetHandle())
            except:
                continue
            break
        else:
            self._hwnd = 0
            raise Exception("Could not grab screenshot, crashed?")

        img = np.frombuffer(bmpstr, dtype=np.uint8)
        img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
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
