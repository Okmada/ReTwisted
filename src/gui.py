import datetime
import os
import re
import sys
import tkinter as tk
import tkinter.font

from roblox import Roblox

VERSION = "2.0"

FONT = "Segoe UI"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Main:
    LBG = "#ccc"

    def __init__(self, master):
        self.root = master

        self.__setup()

    def __setup(self):
        self.root.title("Re²:Twisted")
        self.root.geometry("850x500")
        self.root.resizable(True, True)
        self.root.iconphoto(True, tk.PhotoImage(file=resource_path("icon.png")))

        self.root.defaultFont = tkinter.font.nametofont("TkDefaultFont")
        self.root.defaultFont.configure(family=FONT, size=12)

        self.left_side = tk.Frame(self.root, width=350, background=self.LBG)
        self.left_side.pack(side=tk.LEFT, fill=tk.BOTH)
        self.left_side.pack_propagate(False)

        self.right_side = tk.Frame(self.root)
        self.right_side.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.right_side.pack_propagate(False)

        tk.Label(self.left_side, text="Re²:Twisted", font=(FONT, 20), background=self.LBG) \
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

class RobloxFrame:
    def __new__(self, master, roblox):
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

        def add_text(data):
            text = datetime.datetime.now().strftime("%H:%M:%S") + "\n"
            text += "\n".join([f"{e[0]}: {e[1]}" for e in data.items()]) + "\n"*2

            historyText.config(state=tk.NORMAL)
            historyText.insert("1.0", text)
            historyText.config(state=tk.DISABLED)

        roblox.add_data_callback(add_text)

        # LEFT SIDE

        info_frame = tk.Frame(frame, width=240)
        info_frame.pack_propagate(False)
        info_frame.pack(padx=5, pady=5, side=tk.LEFT, fill=tk.Y)

        tk.Label(info_frame, text=roblox.get_name(), font=(FONT, 16)).pack(side=tk.TOP, pady=(10, 0))

        info_frame_bottom = tk.Frame(info_frame)
        info_frame_bottom.pack(padx=5, pady=5, fill=tk.X, side=tk.BOTTOM)

        enabled_frame = tk.Frame(info_frame_bottom)
        enabled_frame.pack(fill=tk.X, side=tk.TOP)

        enabled_var = tk.IntVar(value=roblox.get_enabled())

        enabled_var.trace_add("write", lambda *e: roblox.set_enabled(bool(enabled_var.get())))

        tk.Label(enabled_frame, text="Enabled") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N)
        tk.Checkbutton(enabled_frame, variable=enabled_var) \
            .pack(side=tk.RIGHT, anchor=tk.W, expand=True)

        lite_mode_frame = tk.Frame(info_frame_bottom)
        lite_mode_frame.pack(fill=tk.X, side=tk.TOP)

        lite_mode_var = tk.IntVar(value=roblox.get_lite_mode())

        lite_mode_var.trace_add("write", lambda *e: roblox.set_lite_mode(bool(lite_mode_var.get())))

        tk.Label(lite_mode_frame, text="Lite mode") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N)
        tk.Checkbutton(lite_mode_frame, variable=lite_mode_var) \
            .pack(side=tk.RIGHT, anchor=tk.W, expand=True)
    
        server_frame = tk.Frame(info_frame_bottom)
        server_frame.pack(fill=tk.X, side=tk.TOP)

        server_url_var = tk.StringVar(value=f"privateServerLinkCode={roblox.get_server()}" if roblox.get_server() else "")

        tk.Label(server_frame, text="Server url:") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N, padx=(0, 5))
        server_url_entry = tk.Entry(server_frame, textvariable=server_url_var, highlightthickness=2)
        server_url_entry.pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.N, expand=True)

        def write_verify_url(*e):
            code = re.search(".*privateServerLinkCode=([0-9]{32}).*", server_url_var.get())
            if code:
                server_url_entry.configure(highlightbackground="#54de01", highlightcolor="#54de01")

                roblox.set_server(int(code.group(1)))
            else:
                server_url_entry.configure(highlightbackground="red", highlightcolor="red")

                roblox.set_server(None)

        server_url_var.trace_add("write", write_verify_url)
        write_verify_url()

class ScrollFrame:
    def __new__(cls, master):
        canvas = tk.Canvas(master)

        scrollbar = tk.Scrollbar(master, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(fill=tk.BOTH, expand=True)

        master.update()

        frame = tk.Frame(canvas)
        frame.bind("<Configure>", lambda event, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")))

        id = canvas.create_window((0, 0), window=frame, anchor=tk.NW, width=canvas.winfo_width()-2)
        canvas.bind("<Configure>", lambda event: canvas.itemconfig(id, width=event.width-2))

        return frame
    
class PauseWindow:
    def __init__(self, master):
        self.root = tk.Toplevel(master, background="red")
        self.root.withdraw()

        self.pause_events = []
        self.unpause_events = []

        self.setup()

    def setup(self):
        self.root.title("Re:Twisted - pop up")
        self.root.geometry("350x150")
        self.root.resizable(False, False)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        red_frame = tk.Frame(self.root)
        red_frame.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)

        frame = tk.Frame(red_frame)
        frame.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Good server have been found", font=(FONT, 16)).pack()
        tk.Label(frame, text="Would you like to continue rerolling?", font=(FONT, 14)).pack()

        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=True)

        tk.Button(buttons_frame, text="Continue rerolling", font=14, command=lambda self=self: [f() for f in self.unpause_events]) \
            .pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        tk.Button(buttons_frame, text="Close and wait", font=14, command=self.close) \
            .pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)        

    def open_and_pause(self):
        [f() for f in self.pause_events]
        self.root.deiconify()

    def close(self):
        self.root.withdraw()
    
class ConfigWindow:
    class ConditionFrame:
        class ConditionGroup:
            class Condition:
                data_options = list(Roblox.Data.FORMAT.keys())
                comparison_options = ["==", "<=", ">="]

                def __init__(self, master, list):
                    self.master = master

                    self.frame = tk.Frame(master, highlightbackground="black", highlightthickness=1)
                    self.frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

                    self.list = list
                    self.list.append(self)

                    self.create_widgets()

                def create_widgets(self):
                    subframe = tk.Frame(self.frame)
                    subframe.pack(fill=tk.BOTH, padx=5, pady=5)

                    self.delete_button = tk.Button(subframe, text="Delete", command=self.delete)
                    self.delete_button.pack(side=tk.RIGHT)

                    self.first_var = tk.StringVar()
                    self.first_var.set(self.data_options[0])

                    tk.OptionMenu(subframe, self.first_var, *self.data_options).pack(side=tk.LEFT)

                    self.second_var = tk.StringVar()
                    self.second_var.set(self.comparison_options[0])

                    self.second_menu = tk.OptionMenu(subframe, self.second_var, *self.comparison_options)
                    self.second_menu.pack(side=tk.LEFT)

                    self.third_var = tk.StringVar()

                    self.third_entry = tk.Entry(subframe, textvariable=self.third_var)
                    self.third_entry.pack(side=tk.LEFT)

                    self.first_var.trace_add("write", self.update_first)
                    self.third_var.trace_add("write", self.update_third)
                    self.update_first()

                def update_first(self, *args):
                    selected = self.first_var.get()
                    data_format = Roblox.Data.FORMAT[selected]

                    self.third_var.set("")

                    if data_format == str:
                        self.second_menu.configure(state="disabled")
                        self.second_var.set("==")
                    else:
                        self.second_menu.configure(state="active")

                def update_third(self, *args):
                    selected = self.first_var.get()
                    data_format = Roblox.Data.FORMAT[selected]
                    input_value = self.third_var.get()

                    if data_format == str:
                        self.third_var.set(input_value.upper())
                    elif data_format == int:
                        self.third_var.set(''.join(c for c in input_value if c in "0123456789"))
                    elif data_format == float:
                        self.third_var.set(''.join(c for c in input_value if c in ".0123456789"))

                def delete(self):
                    self.frame.destroy()
                    self.list.remove(self)

                def import_config(self, config):
                    first_val, second_val, third_val, *_ = config
                    
                    if first_val not in self.data_options:
                        return
                    
                    if second_val not in self.comparison_options:
                        return
                    
                    self.first_var.set(first_val)
                    self.second_var.set(second_val)
                    self.update_first()

                    self.third_var.set(third_val)
                    self.update_third()


                def export_config(self):
                    return [self.first_var.get(), self.second_var.get(), self.third_var.get()]

            def __init__(self, master, list):
                self.master = master

                self._sublist = []

                self.frame = tk.Frame(master, highlightbackground="black", highlightthickness=2)
                self.frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

                self._list = list
                self._list.append(self)

                self.create_widgets()

            def create_widgets(self):
                subframe = tk.Frame(self.frame)
                subframe.pack(fill=tk.BOTH, padx=5, pady=5)

                self.add_condition_button = tk.Button(subframe, text="Add condition", command=self.add_condition)
                self.add_condition_button.pack(fill=tk.X, side=tk.LEFT)
                
                self.delete_group_button = tk.Button(subframe, text="Delete group", command=self.delete_group)
                self.delete_group_button.pack(fill=tk.X, side=tk.RIGHT)

            def add_condition(self):
                self.Condition(self.frame, self._sublist)

            def delete_group(self):
                self.frame.destroy()
                self._list.remove(self)

            def import_config(self, config):
                for subconfig in config:
                    self.Condition(self.frame, self._sublist) \
                        .import_config(subconfig)

            def export_config(self):
                return [condintion.export_config() for condintion in self._sublist]

        def __init__(self, master):
            self.scroll_frame = ScrollFrame(master)    

            self._sublist = []            

            tk.Button(self.scroll_frame, text="Add group", command=lambda:
                      self.ConditionGroup(self.scroll_frame, self._sublist)) \
                .pack(fill=tk.X, side=tk.BOTTOM)

        def import_config(self, config):
            [group.frame.destroy() for group in self._sublist]
            self._sublist = []            

            for subconfig in config:
                self.ConditionGroup(self.scroll_frame, self._sublist) \
                    .import_config(subconfig)

        def export_config(self):
            return [group.export_config() for group in self._sublist]

    class ConfigFrame:
        TEMPLATE = {
            "webhook": {
                "url": [str, "",
                        "Webhook url where message will be sent on successful find.\nLeave empty for no message."],
                "role id": [str, "",
                            "Role which will be pinged in message."],
                "user id": [str, "",
                            "User which will be pinged in message."]
            },
            "timeout": [int, 60, "Maximum amount of time that the server can take to reroll.\nEntring 0 will disable timeout feature."]
        }

        def __init__(self, master):
            canvas = tk.Canvas(master)
            frame = tk.Frame(canvas)

            vscrollbar = tk.Scrollbar(master, orient=tk.VERTICAL, command=canvas.yview)
            vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.configure(yscrollcommand=vscrollbar.set)

            hscrollbar = tk.Scrollbar(master, orient=tk.HORIZONTAL, command=canvas.xview)
            hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            canvas.configure(xscrollcommand=hscrollbar.set)

            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            canvas.create_window((0, 0), window=frame, anchor=tk.NW)

            frame.bind("<Configure>", \
                   lambda event, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")))
            
            self._config_list = []
            self._generateConfig(frame, self.TEMPLATE)
            
        def _generateConfig(self, master, template, path=[]):
            if path:
                last = path[-1].capitalize()

                master = tk.Frame(master)
                master.pack(anchor=tk.W, padx=(max(0, (len(path) - 1) * 25), 0))

                tk.Label(master, text=last).pack(anchor=tk.W)

            match template:
                case dict():
                    for key, item in template.items():
                        self._generateConfig(master, item, path=path + [key])
                case list():
                    data_type, default, desc, *_ = template

                    inpt = tk.StringVar()
                    inpt.dtype = data_type
                    inpt.default = default
                    
                    def validate(*e):
                        if data_type == int:
                            inpt.set(''.join(c for c in inpt.get() if c in "0123456789"))

                    inpt.trace_add("write", validate)

                    self._config_list.append((path, inpt))

                    tk.Label(master, state=tk.DISABLED, text=desc, font=(FONT, 10), 
                             anchor=tk.W, justify=tk.LEFT) \
                        .pack(fill=tk.X, side=tk.TOP, padx=(3, 0))

                    tk.Entry(master, textvariable=inpt, width=50) \
                        .pack(pady=(0, 15), side=tk.LEFT, padx=(3, 0))
                    
        def import_config(self, config):
            for path, inpt in self._config_list:
                inpt.set(self._get_in_dict(config, path) or inpt.default)

        def export_config(self):
            config = {}
            for path, inpt in self._config_list:
                tmp = config
                for i, arg in zip(range(len(path))[::-1], path):
                    if i != 0:
                        if arg not in tmp:
                            tmp[arg] = {}
                        tmp = tmp[arg]
                    else:
                        tmp[arg] = inpt.get()
            return config

        @staticmethod
        def _get_in_dict(config, path):
            tmp = config
            for arg in path:
                if arg in tmp:
                    tmp = tmp[arg]
                    continue
                return None
            return tmp

    def __init__(self, master, config) -> None:
        self.root= tk.Toplevel(master)
        self.root.withdraw()

        self.config = config

        self.__setup()

    def __setup(self):
        self.root.title("Re:Twisted - config")
        self.root.geometry("1000x600")
        self.root.resizable(True, True)

        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close())

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Button(bottom_frame, text="Save", command=lambda: self.close_and_save()) \
            .pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

        tk.Button(bottom_frame, text="Close", command=lambda: self.close()) \
            .pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5, pady=5)
        
        left_side = tk.Frame(self.root)
        left_side.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_side.pack_propagate(False)

        right_side = tk.Frame(self.root)
        right_side.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        right_side.pack_propagate(False)

        # LEFT SIDE
        self.config_frame = self.ConfigFrame(left_side)

        # RIGHT SIDE
        self.condition_frame = self.ConditionFrame(right_side)

    def open(self):
        self.config_frame.import_config(self.config.get(["config"]) or {})
        self.condition_frame.import_config(self.config.get(["conditions"]) or [])

        self.root.deiconify()

    def close(self):
        self.root.withdraw()

    def close_and_save(self):
        self.close()

        self.config.set(["config"], self.config_frame.export_config())
        self.config.set(["conditions"], self.condition_frame.export_config())
