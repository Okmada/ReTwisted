import ctypes
import ctypes.wintypes
import enum
import logging
import os
import time

import simplecv as scv
from capture.d3dcapture import CaptureSession
from config import ConfigManager

user32 = ctypes.windll.user32

WM_CLOSE = 0x10

MONITOR_DEFAULTTOPRIMARY = 0x1

class MonitorInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork", ctypes.wintypes.RECT),
                ("dwFlags", ctypes.c_uint)]

class RobloxTypes(enum.Enum):
    WINDOWSCLIENT = "Roblox Player"
    ApplicationFrameWindow = "Microsoft Roblox"

class Roblox:
    def __init__(self, roblox_type: RobloxTypes):
        assert roblox_type in RobloxTypes

        self._capture_session = CaptureSession()
        self._capture_session.frame_callback = self._frame_callback
        self._last_frame = None
        self._last_frame_time = 0

        self._roblox_type = roblox_type

    def start_roblox(self, arg):
        match self._roblox_type:
            case RobloxTypes.WINDOWSCLIENT:
                os.popen('powershell.exe -Command "Get-Process -Name RobloxPlayerBeta -ErrorAction Ignore | Sort-Object -Property CPU -Descending | Select-Object -Skip 1 | ForEach-Object {$_.Kill()}"')

                programs_dir = os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs")

                path = os.path.join(programs_dir, "Roblox\\Roblox Player.lnk")

                override_path = ConfigManager().get(["roblox player launcher override"])
                if override_path:
                    if os.path.isfile(override_path):
                        path = override_path
                    else:
                        logging.warning("Invalid Roblox Player override, using default Roblox Player instead.")

                if not os.path.isfile(path):
                    raise Exception("Roblox is not installed")

                os.popen(f'powershell.exe -Command Start-Process -FilePath \\"{path}\\" -ArgumentList \\"{arg}\\"')
            case RobloxTypes.ApplicationFrameWindow:
                if not bool(os.popen("powershell.exe Get-AppxPackage -Name ROBLOXCORPORATION.ROBLOX").read().strip()):
                    raise Exception("Roblox is not installed")

                os.popen(f'powershell.exe -Command Start-Process \\"{arg}\\"')
            case _:
                return None

    def join_place(self, place_id: str, linkCode=""):
        assert place_id.isnumeric()
        arg = f"roblox://placeId={place_id}" + (f"&linkCode={linkCode}" if linkCode else "")
        self.start_roblox(arg)

    def join_server(self, code: str):
        assert len(code) == 32
        arg = f"roblox://navigation/share_links?code={code}&type=Server"
        self.start_roblox(arg)

    def close_roblox(self):
        self._capture_session.stop()
        match self._roblox_type:
            case RobloxTypes.WINDOWSCLIENT:
                os.popen('powershell.exe -Command "Get-Process -Name RobloxPlayerBeta -ErrorAction Ignore | ForEach-Object {$_.Kill()}"')
            case RobloxTypes.ApplicationFrameWindow:
                if hwnd := self.hwnd: 
                    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

    def get_frame(self):
        if (time.time() - self._last_frame_time) > 5:
            self.recreate_capture()
            self._last_frame_time = time.time()

        frame = self._last_frame
        self._last_frame = None
        return frame

    def recreate_capture(self):
        hwnd = self.hwnd

        logging.debug("Recreating capture")

        if hwnd and user32.IsWindow(hwnd):
            try:
                self._capture_session.stop()
                self._capture_session.start(hwnd, capture_cursor=False)
            except Exception as e:
                logging.debug("Failed to recreate capture: " + str(e))

    def is_crashed(self):
        hwnd = self.hwnd
        if not self.hwnd:
            return True

        if self._roblox_type == RobloxTypes.WINDOWSCLIENT:
            if win := user32.FindWindowW(None, "Roblox Crash"):
                user32.PostMessageW(win, WM_CLOSE, 0, 0)
                return True
            
        return not user32.IsWindow(hwnd)

    def is_fullscreen(self) -> bool:
        hwnd = self.hwnd
        if not hwnd:
            return False

        window_monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTOPRIMARY)

        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)

        if not user32.GetMonitorInfoW(window_monitor, ctypes.byref(info)):
            return False

        window_rect = ctypes.wintypes.RECT()

        if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
            return False

        return bytes(window_rect) == bytes(info.rcMonitor)

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
        return user32.FindWindowW(self._roblox_type.name, "Roblox")

    @property
    def _borders(self):
        hwnd = self.hwnd
        if not hwnd:
            return 0, 0

        if self.is_fullscreen():
            return 0, 0

        crect = ctypes.wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(crect))

        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))

        edge = (rect.right - rect.left - crect.right + crect.left) / 2
        match self._roblox_type:
            case RobloxTypes.ApplicationFrameWindow:
                if user32.IsZoomed(hwnd):
                    topedge = 40
                else:
                    topedge = 33
            case RobloxTypes.WINDOWSCLIENT:
                topedge = 31

        return edge, topedge

    def _frame_callback(self, *event):
        frame = self._capture_session.get_frame()

        if frame is None:
            return

        scale_factor = 1
        if hwnd := self.hwnd:
            scale_factor = user32.GetDpiForWindow(hwnd) / 96.0

        edge, topedge = self._borders

        if not self.is_fullscreen():
            scaled_edge, scaled_topedge = round(edge * scale_factor), round(topedge * scale_factor)
            frame = frame[scaled_topedge:-1, 1:-1]

        frame = scv.upscale(frame, 1 / scale_factor)

        self._last_frame_time = time.time()
        self._last_frame = frame