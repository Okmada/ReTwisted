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
from macro.macros import DefaultMacro, Macros

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
    def __new__(self, master, macro: MacroHandler):
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

        enabled_var = tk.IntVar(value=ConfigManager().get(config_path + ["enabled"]))
        enabled_var.trace_add("write", lambda *e: ConfigManager().set(config_path + ["enabled"], bool(enabled_var.get())))

        tk.Label(enabled_frame, text="Enabled") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N)
        tk.Checkbutton(enabled_frame, variable=enabled_var) \
            .pack(side=tk.RIGHT, anchor=tk.W, expand=True)


        macro_frame = tk.Frame(info_frame_bottom)
        macro_frame.pack(fill=tk.X, side=tk.TOP)

        macro_var = tk.StringVar(value=ConfigManager().get(config_path + ["macro"]))

        tk.Label(macro_frame, text="Macro:") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N, padx=(0, 5))
        server_url_entry = tk.OptionMenu(macro_frame, macro_var, *Macros.keys())
        server_url_entry.pack(fill=tk.BOTH, side=tk.LEFT, anchor=tk.N)

        def write_verify_macro(*e):
            selected_macro = macro_var.get()
            if selected_macro not in Macros:
                selected_macro = DefaultMacro
            macro_var.set(selected_macro)
            macro.change_macro(selected_macro)
            ConfigManager().set(config_path + ["macro"], selected_macro)

        macro_var.trace_add("write", write_verify_macro)
        write_verify_macro()


        server_frame = tk.Frame(info_frame_bottom)
        server_frame.pack(fill=tk.X, side=tk.TOP)

        server = ConfigManager().get(config_path + ["server"])
        server_url_var = tk.StringVar(value=f"privateServerLinkCode={server}" if server else "")

        tk.Label(server_frame, text="Server url:") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N, padx=(0, 5))
        server_url_entry = tk.Entry(server_frame, textvariable=server_url_var, highlightthickness=2)
        server_url_entry.pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.N, expand=True)

        def write_verify_url(*e):
            linkCode = re.search(".*privateServerLinkCode=([0-9]{32}).*", server_url_var.get())
            code = re.search(".*code=([a-z0-9]{32}).*", server_url_var.get())

            if code:
                popup = tk.Toplevel(master)
                popup.resizable(False, False)
                popup.title("Wrong link detected!")
                tk.Label(popup, justify=tk.LEFT, text="An incorrect link has been detected. Follow these steps to obtain the correct link:\n\n1) Open the current link in a browser where you are logged into Roblox.\n2) Wait a few seconds for Roblox to redirect and launch.\n3) Copy the link from the address bar and paste it in.").pack(padx=10, pady=10)
                server_url_var.set("")
                popup.grab_set()
                popup.focus()

            color = "#54de01" if linkCode else "red"
            server_url_entry.configure(highlightbackground=color, highlightcolor=color)

            server = str(linkCode.group(1)) if linkCode else ""
            ConfigManager().set(config_path + ["server"], server)

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

            image = macro.roblox.get_frame()
            if image is None:
                if hasattr(button, "timer"):
                    button.timer.cancel()
                button.timer = threading.Timer(1.5, lambda: screenshot_button.config(text=screenshot_button.original_text))
                button.timer.start()
                button.config(text="Could not grab screenshot")
                return
            
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
