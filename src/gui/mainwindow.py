import tkinter as tk
import tkinter.font

import utils
from constants import FONT, NAME, VERSION
from gui.scrollframe import ScrollFrame


class MainWindow:
    LBG = "#ccc"

    def __init__(self, master) -> None:
        self.root = master

        self._setup()

    def _setup(self) -> None:
        self.root.title(NAME)
        self.root.geometry("850x500")
        self.root.resizable(True, True)
        self.root.iconphoto(True, tk.PhotoImage(file=utils.resource_path("icon.png")))

        self.root.defaultFont = tkinter.font.nametofont("TkDefaultFont")
        self.root.defaultFont.configure(family=FONT, size=12)

        self.left_side = tk.Frame(self.root, width=350, background=self.LBG)
        self.left_side.pack(side=tk.LEFT, fill=tk.BOTH)
        self.left_side.pack_propagate(False)

        self.right_side = tk.Frame(self.root)
        self.right_side.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.right_side.pack_propagate(False)

        tk.Label(self.left_side, text=NAME, font=(FONT, 20), background=self.LBG) \
            .pack(side=tk.TOP)

        tk.Label(self.left_side, text=f"version {VERSION}", font=(FONT, 12), background=self.LBG) \
            .pack(side=tk.TOP, pady=(0, 15))

        self.status = tk.Label(self.left_side, text="Status - Paused", background=self.LBG)
        self.status.pack(side=tk.TOP)

        server_buttons = tk.Frame(self.left_side, background=self.LBG)
        server_buttons.pack(fill=tk.X, side=tk.TOP)

        self.unpause_events = [lambda: self.status.config(text="Status - Running")]
        tk.Button(server_buttons, text="Start", command=lambda *e: [f() for f in self.unpause_events]) \
            .pack(fill=tk.X, side=tk.LEFT, anchor=tk.N, pady=5, padx=5, expand=True)

        self.pause_events = [lambda: self.status.config(text="Status - Paused")]
        tk.Button(server_buttons, text="Pause", command=lambda *e: [f() for f in self.pause_events]) \
            .pack(fill=tk.X, side=tk.RIGHT, anchor=tk.N, pady=5, padx=5, expand=True)

        self.config_events = []
        tk.Button(self.left_side, text="Settings", command=lambda: [f() for f in self.config_events]) \
            .pack(fill=tk.X, side=tk.TOP, pady=5, padx=5)

        # tk.Label(self.left_side, text="Records", background=self.LBG) \
        #     .pack(side=tk.TOP)

        # self.records_scrollframe = ScrollFrame(self.left_side)

        self.games_scrollframe = ScrollFrame(self.right_side)
        self.games_scrollframe.pack(fill=tk.BOTH, expand=True)
