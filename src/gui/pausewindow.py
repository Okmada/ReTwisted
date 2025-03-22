import datetime
import threading
import time
import tkinter as tk

from config import ConfigManager
from constants import FONT, NAME


class PauseWindow:
    def __init__(self, master) -> None:
        self.root = tk.Toplevel(master, background="red")
        self.root.withdraw()

        self.pause_events = []
        self.unpause_events = []

        self._timer = None

        self._setup()

    def _setup(self):
        self.root.title(f"{NAME} - pop up")
        self.root.geometry("360x150")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        red_frame = tk.Frame(self.root)
        red_frame.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)

        frame = tk.Frame(red_frame)
        frame.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Good server has been found", font=(FONT, 16)).pack()
        tk.Label(frame, text="Would you like to continue rerolling?", font=(FONT, 14)).pack()

        self.timer_text = tk.Label(frame, text="If not closed will continue to reroll in n minutes (00:00)", font=(FONT, 10))
        self.timer_text.pack()

        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=True)

        tk.Button(buttons_frame, text="Continue rerolling", font=14, command=self.unpause_all) \
            .pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        tk.Button(buttons_frame, text="Close and wait", font=14, command=self.close) \
            .pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)

    def unpause_all(self) -> None:
        for f in self.unpause_events: f()

    def pause_all(self) -> None:
        for f in self.pause_events: f()

    def start_timer(self):
        timer_mins = ConfigManager().get(["resume timer"])

        if not timer_mins:
            self.timer_text.config(text="")
            return

        timestamp = datetime.datetime.fromtimestamp(time.time() + timer_mins * 60).strftime("%H:%M")
        self.timer_text.config(text=f"If not closed will continue to reroll in {timer_mins} minutes ({timestamp})")

        self.cancel_timer()

        self._timer = threading.Timer(timer_mins * 60, self.unpause_all)
        self._timer.start()

    def cancel_timer(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def open(self):
        self.pause_all()

        self.root.deiconify()

        self.start_timer()

    def close(self):
        self.root.withdraw()

        self.cancel_timer()