import ctypes
import ctypes.wintypes
import logging
import threading
import time
from typing import Callable, List, Tuple
from utils import Singleton

user32 = ctypes.windll.user32

SM_XVIRTUALSCREEN = 0x4C
SM_YVIRTUALSCREEN = 0x4D

SM_CXVIRTUALSCREEN = 0x4E
SM_CYVIRTUALSCREEN = 0x4F

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_LEFTCLICK = MOUSEEVENTF_LEFTDOWN + MOUSEEVENTF_LEFTUP

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

PUL = ctypes.POINTER(ctypes.c_ulong)

DESKTOP = user32.GetDesktopWindow()

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class InputI(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", InputI)]

def get_window_rect(hwnd: int) -> List[int]:
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom

def get_class_name(hwnd: int) -> str:
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_name, 256)
    return class_name.value

class Controller(threading.Thread, metaclass=Singleton):
    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.name = "Controller"

        self.queue = []
        self.queue_event = threading.Event()

        self.pause_event = threading.Event()

        self.start()

    def add_to_queue(self, func: Callable) -> None:
        self.queue.append(func)
        self.queue_event.set()

    def pause(self) -> None:
        self.pause_event.clear()

    def unpause(self) -> None:
        self.pause_event.set()

    @staticmethod
    def focus_window(win: int) -> None:
        ALT = 0x38

        Controller._key_down(ALT)
        try:
            user32.SetForegroundWindow(win)
        finally:
            Controller._key_up(ALT)

    @staticmethod
    def _move_to(x: int, y: int) -> None:
        x_offset = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y_offset = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)

        virtual_width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        virtual_height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

        x, y = x - x_offset, y - y_offset
        x, y = round(x * 65535 / virtual_width), round(y * 65535 / virtual_height)

        extra = ctypes.c_ulong(0)
        ii_ = InputI()
        ii_.mi = MouseInput(x, y, 0, (MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK), 0, ctypes.pointer(extra))
        command = Input(ctypes.c_ulong(0), ii_)
        user32.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))

    @staticmethod
    def _left_click() -> None:
        extra = ctypes.c_ulong(0)
        ii_ = InputI()
        ii_.mi = MouseInput(0, 0, 0, MOUSEEVENTF_LEFTCLICK, 0, ctypes.pointer(extra))
        command = Input(ctypes.c_ulong(0), ii_)
        user32.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))

    @staticmethod
    def _click_in_window(win: int, point: Tuple[int, int]) -> None:
        x, y = point
        mx, my, *_ = get_window_rect(win)
        fx, fy = mx + x, my + y

        Controller.focus_window(win)

        if get_class_name(win) == "WINDOWSCLIENT":
            time.sleep(.1)
            Controller.focus_window(DESKTOP)

        time.sleep(.1)

        Controller._move_to(fx, fy)

        time.sleep(.1)

        if get_class_name(win) == "WINDOWSCLIENT":
            Controller._left_click()

        Controller._left_click()

    def async_click(self, win: int, point: Tuple[int, int]) -> None:
        func = lambda: self._click_in_window(win, point)
        self.add_to_queue((func,))

    def sync_click(self, win: int, point: Tuple[int, int]) -> None:
        continue_event = threading.Event()

        func = lambda: self._click_in_window(win, point)
        self.add_to_queue((func, continue_event.set))

        continue_event.wait()

    @staticmethod
    def _key_down(key: int) -> None:
        keybdFlags = KEYEVENTF_SCANCODE

        extra = ctypes.c_ulong(0)
        ii_ = InputI()
        ii_.ki = KeyBdInput(0, key, keybdFlags, 0, ctypes.pointer(extra))
        command = Input(ctypes.c_ulong(1), ii_)
        user32.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))

    @staticmethod
    def _key_up(key: int) -> None:
        keybdFlags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP

        extra = ctypes.c_ulong(0)
        ii_ = InputI()
        ii_.ki = KeyBdInput(0, key, keybdFlags, 0, ctypes.pointer(extra))
        command = Input(ctypes.c_ulong(1), ii_)
        user32.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))

    @staticmethod
    def _press_key(win: int, key: int, delay=.25) -> None:
        Controller.focus_window(win)

        Controller._key_down(key)

        time.sleep(delay)

        Controller._key_up(key)

    def async_press_key(self, win: int, key: int) -> None:
        func = lambda: self._press_key(win, key)
        self.add_to_queue((func,))

    def sync_press_key(self, win: int, key: int) -> None:
        continue_event = threading.Event()

        func = lambda: self._press_key(win, key)
        self.add_to_queue((func, continue_event.set))

        continue_event.wait()

    def run(self):
        while True:
            self.queue_event.wait()
            self.pause_event.wait()

            if self.queue:
                for func in self.queue.pop(0):
                    try:
                        func()
                    except Exception as e:
                        logging.error(str(e))

                time.sleep(.5)
            else:
                self.queue_event.clear()
