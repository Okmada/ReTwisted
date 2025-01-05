import ctypes
import ctypes.wintypes
import datetime
import re
import threading
import tkinter as tk

import cv2

from config import ConfigManager
from constants import FONT
from data import Data
from macro.macrohandler import MacroHandler

CF_DIB = 8
NO_ERROR = 0
GMEM_MOVEABLE = 0x0002

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

GlobalLock = kernel32.GlobalLock
GlobalLock.argtypes = ctypes.wintypes.HGLOBAL,
GlobalLock.restype = ctypes.wintypes.LPVOID
GlobalAlloc = kernel32.GlobalAlloc
GlobalAlloc.argtypes = ctypes.wintypes.UINT, ctypes.c_size_t
GlobalAlloc.restype = ctypes.wintypes.HGLOBAL
GlobalUnlock = kernel32.GlobalUnlock
GlobalUnlock.argtypes = ctypes.wintypes.HGLOBAL,
GlobalUnlock.restype = ctypes.wintypes.BOOL

OpenClipboard = user32.OpenClipboard
OpenClipboard.argtypes = ctypes.wintypes.HWND,
OpenClipboard.restype = ctypes.wintypes.BOOL
GetClipboardData = user32.GetClipboardData
GetClipboardData.argtypes = ctypes.wintypes.UINT,
GetClipboardData.restype = ctypes.wintypes.HANDLE
SetClipboardData = user32.SetClipboardData
SetClipboardData.argtypes = ctypes.wintypes.UINT, ctypes.wintypes.HANDLE
SetClipboardData.restype = ctypes.wintypes.HANDLE
CloseClipboard = user32.CloseClipboard
CloseClipboard.argtypes = ()
CloseClipboard.restype = ctypes.wintypes.BOOL
EmptyClipboard = user32.EmptyClipboard
EmptyClipboard.argtypes = ()
EmptyClipboard.restype = ctypes.wintypes.BOOL



class RobloxFrame:
    def __new__(self, master, macro: MacroHandler, config: ConfigManager):
        config_path = ["roblox", macro.roblox.name]

        frame = tk.Frame(master, height=250, background="#aaa")
        frame.pack(padx=5, pady=5, fill=tk.X)
        frame.pack_propagate(False)

        # RIGHT SIDE

        history_frame = tk.Frame(frame)
        history_frame.pack_propagate(False)
        history_frame.pack(padx=5, pady=5, side=tk.RIGHT, fill=tk.BOTH, expand=True)

        historyText = tk.Text(history_frame, state=tk.DISABLED)
        scrollbar = tk.Scrollbar(history_frame, command=historyText.yview)
        historyText['yscrollcommand'] = scrollbar.set

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        historyText.pack(expand=True, fill=tk.X)

        def add_text(data: Data):
            text = datetime.datetime.now().strftime("%H:%M:%S") + "\n"
            text += "\n".join([f"{e[0]}: {e[1]}" for e in data.items()]) + "\n"*2

            historyText.config(state=tk.NORMAL)
            historyText.insert("1.0", text)
            historyText.config(state=tk.DISABLED)

        macro.add_data_callback(add_text)

        # LEFT SIDE

        info_frame = tk.Frame(frame, width=240)
        info_frame.pack_propagate(False)
        info_frame.pack(padx=5, pady=5, side=tk.LEFT, fill=tk.Y)

        tk.Label(info_frame, text=macro.roblox.friendly_name, font=(FONT, 16)).pack(side=tk.TOP, pady=(10, 0))

        info_frame_bottom = tk.Frame(info_frame)
        info_frame_bottom.pack(padx=5, pady=5, fill=tk.X, side=tk.BOTTOM)

        enabled_frame = tk.Frame(info_frame_bottom)
        enabled_frame.pack(fill=tk.X, side=tk.TOP)

        enabled_var = tk.IntVar(value=config.get(config_path + ["enabled"]))

        enabled_var.trace_add("write", lambda *e: config.set(config_path + ["enabled"], bool(enabled_var.get())))

        tk.Label(enabled_frame, text="Enabled") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N)
        tk.Checkbutton(enabled_frame, variable=enabled_var) \
            .pack(side=tk.RIGHT, anchor=tk.W, expand=True)

        server_frame = tk.Frame(info_frame_bottom)
        server_frame.pack(fill=tk.X, side=tk.TOP)

        server = config.get(config_path + ["server"])
        server_url_var = tk.StringVar(value=f"code={server}" if server else "")

        tk.Label(server_frame, text="Server url:") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N, padx=(0, 5))
        server_url_entry = tk.Entry(server_frame, textvariable=server_url_var, highlightthickness=2)
        server_url_entry.pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.N, expand=True)

        def write_verify_url(*e):
            code = re.search(".*code=([a-z0-9]{32}).*", server_url_var.get())

            color = "#54de01" if code else "red"
            server_url_entry.configure(highlightbackground=color, highlightcolor=color)

            server = str(code.group(1)) if code else ""
            config.set(config_path + ["server"], server)

        server_url_var.trace_add("write", write_verify_url)
        write_verify_url()

        def copy_screenshot(button):
            if not macro.roblox.hwnd:
                if hasattr(button, "timer"):
                    button.timer.cancel()
                button.timer = threading.Timer(1.5, lambda: screenshot_button.config(text=screenshot_button.original_text))
                button.timer.start()
                button.config(text="Roblox not found")
                return

            image = macro.roblox.get_screenshot()
            buffer = cv2.imencode(".bmp", image)[1].tobytes()[14:]

            OpenClipboard(None)
            EmptyClipboard()
            hmem = GlobalAlloc(GMEM_MOVEABLE, len(buffer))
            pmem = GlobalLock(hmem)
            ctypes.memmove(pmem, buffer, len(buffer))
            GlobalUnlock(hmem)
            SetClipboardData(CF_DIB, hmem)
            CloseClipboard()

        screenshot_button = tk.Button(info_frame_bottom, text="Copy screenshot")
        screenshot_button.original_text = screenshot_button.cget("text")
        screenshot_button.config(command=lambda: copy_screenshot(screenshot_button))
        screenshot_button.pack(fill=tk.X, side=tk.TOP, pady=(3, 0))
