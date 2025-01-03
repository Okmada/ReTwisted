import ctypes
import ctypes.wintypes
import enum
import logging
import os
import time

import cv2
import numpy as np

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

CHAT_COLOR = (248, 247, 247)
CHAT_BB = {"left": 126, "top": 23, "right": 150, "bottom": 45}

WM_CLOSE = 0x10

SRCCOPY = 0xCC0020

MONITOR_DEFAULTTOPRIMARY = 0x1

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

class MonitorInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork", ctypes.wintypes.RECT),
                ("dwFlags", ctypes.c_uint)]

class RobloxTypes(enum.Enum):
    WINDOWSCLIENT = "Roblox Player"
    ApplicationFrameWindow = "UWP Roblox"

class Roblox:
    def __init__(self, roblox_type: RobloxTypes):
        assert roblox_type in RobloxTypes

        self._roblox_type = roblox_type
        self._hwnd: int = 0

    def start_roblox(self, arg, bloxstrap=False):
        if not self.is_installed():
            raise Exception("Roblox is not installed")

        match self._roblox_type:
            case RobloxTypes.WINDOWSCLIENT:
                programs_dir = os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs")

                path = os.path.join(programs_dir, "Roblox\\Roblox Player.lnk")

                if bloxstrap:
                    bloxstrap_path = os.path.join(programs_dir, "Bloxstrap.lnk")

                    if os.path.isfile(bloxstrap_path):
                        path = bloxstrap_path
                    else:
                        logging.warning("Could not find Bloxstrap, using Roblox Player instead.")

                os.startfile(path, arguments=arg)
            case RobloxTypes.ApplicationFrameWindow:
                os.startfile(arg)
            case _:
                return None

        self.find_roblox()

    def join_place(self, place_id: str, linkCode="", bloxstrap=False):
        assert place_id.isnumeric()
        arg = f"roblox://placeId={place_id}" + (f"&linkCode={linkCode}" if linkCode else "")
        self.start_roblox(arg, bloxstrap=bloxstrap)

    def join_server(self, code: str, bloxstrap=False):
        assert len(code) == 32
        arg = f"roblox://navigation/share_links?code={code}&type=Server"
        self.start_roblox(arg, bloxstrap=bloxstrap)

    def find_roblox(self, retries=20):
        for _ in range(retries):
            if hwnd := user32.FindWindowW(self._roblox_type.name, "Roblox"):
                self._hwnd = hwnd
                break
            time.sleep(1)
        else:
            raise Exception("Could not find roblox")

    def close_roblox(self, retries=20):
        if not self._hwnd:
            return

        user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)

        for _ in range(retries):
            if not user32.FindWindowW(self._roblox_type.name, "Roblox"):
                self._hwnd = 0
                break
            time.sleep(1)
        else:
            logging.error("Could not close Roblox.")

    def is_installed(self):
        match self._roblox_type:
            case RobloxTypes.WINDOWSCLIENT:
                programs_dir = os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs")
                path = os.path.join(programs_dir, "Roblox\\Roblox Player.lnk")
                return os.path.isfile(path)
            case RobloxTypes.ApplicationFrameWindow:
                return bool(os.popen("powershell.exe Get-AppxPackage -Name ROBLOXCORPORATION.ROBLOX").read().strip())
            case _:
                return False

    def is_crashed(self):
        if self._hwnd == 0:
            return False

        if self._roblox_type == RobloxTypes.WINDOWSCLIENT:
            if win := user32.FindWindowW(None, "Roblox Crash"):
                user32.PostMessageW(win, WM_CLOSE, 0, 0)
                self._hwnd = 0
                return True

        if not user32.IsWindow(self._hwnd):
            self._hwnd = 0
            return True
        else:
            return False

    def is_fullscreen(self) -> bool:
        if not self._hwnd:
            return False

        window_monitor = user32.MonitorFromWindow(self._hwnd, MONITOR_DEFAULTTOPRIMARY)

        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)

        if not user32.GetMonitorInfoW(window_monitor, ctypes.byref(info)):
            return False

        window_rect = ctypes.wintypes.RECT()

        if not user32.GetWindowRect(self._hwnd, ctypes.byref(window_rect)):
            return False

        return bytes(window_rect) == bytes(info.rcMonitor)

    def is_chat_open(self):
        img = self.get_screenshot()

        chat_slice = img[CHAT_BB["top"]:CHAT_BB["bottom"], CHAT_BB["left"]:CHAT_BB["right"]]
        ratio = np.count_nonzero(np.all(chat_slice == CHAT_COLOR, axis=2)) / np.multiply(*chat_slice.shape[:2])

        return ratio >= .25

    def get_chat_pos(self):
        return self.offset_point(((CHAT_BB["left"] + CHAT_BB["right"]) // 2, (CHAT_BB["top"] + CHAT_BB["bottom"]) // 2))

    def get_screenshot(self):
        if not user32.IsWindow(self._hwnd):
            return None

        scale_factor = user32.GetDpiForWindow(self._hwnd) / 96.0

        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(self._hwnd, ctypes.byref(rect))

        unscaled_w, unscaled_h = rect.right - rect.left, rect.bottom - rect.top
        scaled_w, scaled_h = round(unscaled_w * scale_factor), round(unscaled_h * scale_factor)

        hwndDC = user32.GetWindowDC(self._hwnd)
        mfcDC = gdi32.CreateCompatibleDC(hwndDC)

        saveBitMap = gdi32.CreateCompatibleBitmap(hwndDC, scaled_w, scaled_h)
        gdi32.SelectObject(mfcDC, saveBitMap)

        user32.PrintWindow(self._hwnd, mfcDC, 2)

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

        edge, topedge = self._borders

        if not self.is_fullscreen():
            scaled_edge, scaled_topedge = round(edge * scale_factor), round(topedge * scale_factor)
            img = img[scaled_topedge:-scaled_edge, scaled_edge:-scaled_edge]

        out_dims = int(unscaled_w - 2 * edge), int(unscaled_h - (edge + topedge))
        img = cv2.resize(img, out_dims, interpolation=cv2.INTER_NEAREST)

        return img.astype(dtype=np.uint8)

    def offset_point(self, point):
        ox, oy = map(round, self._borders)
        return (point[0] + ox, point[1] + oy)

    @property
    def friendly_name(self):
        return self._roblox_type.value

    @property
    def name(self):
        return self._roblox_type.name

    @property
    def hwnd(self):
        return self._hwnd

    @property
    def _borders(self):
        if self.is_fullscreen():
            return 0, 0

        crect = ctypes.wintypes.RECT()
        user32.GetClientRect(self._hwnd, ctypes.byref(crect))

        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(self._hwnd, ctypes.byref(rect))

        edge = (rect.right - rect.left - crect.right + crect.left) / 2
        match self._roblox_type:
            case RobloxTypes.ApplicationFrameWindow:
                if user32.IsZoomed(self._hwnd):
                    topedge = 40
                else:
                    topedge = 33
            case RobloxTypes.WINDOWSCLIENT:
                topedge = 31

        return edge, topedge
