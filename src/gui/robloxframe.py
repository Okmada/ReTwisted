import datetime
import re
import tkinter as tk

from config import ConfigManager
from constants import FONT
from macro import Data, Macro


class RobloxFrame:
    def __new__(self, master, macro: Macro, config: ConfigManager):
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

        enabled_var = tk.IntVar(value=config.get([macro.roblox.name, "enabled"]))

        enabled_var.trace_add("write", lambda *e: config.set([macro.roblox.name, "enabled"], bool(enabled_var.get())))

        tk.Label(enabled_frame, text="Enabled") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N)
        tk.Checkbutton(enabled_frame, variable=enabled_var) \
            .pack(side=tk.RIGHT, anchor=tk.W, expand=True)

        server_frame = tk.Frame(info_frame_bottom)
        server_frame.pack(fill=tk.X, side=tk.TOP)

        server = config.get([macro.roblox.name, "server"])
        server_url_var = tk.StringVar(value=f"privateServerLinkCode={server}" if server else "")

        tk.Label(server_frame, text="Server url:") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N, padx=(0, 5))
        server_url_entry = tk.Entry(server_frame, textvariable=server_url_var, highlightthickness=2)
        server_url_entry.pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.N, expand=True)

        def write_verify_url(*e):
            code = re.search(".*privateServerLinkCode=([0-9]{32}).*", server_url_var.get())

            color = "#54de01" if code else "red"
            server_url_entry.configure(highlightbackground=color, highlightcolor=color)

            server = str(code.group(1)) if code else ""
            config.set([macro.roblox.name, "server"], server)

        server_url_var.trace_add("write", write_verify_url)
        write_verify_url()
