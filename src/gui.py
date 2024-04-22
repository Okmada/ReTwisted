import datetime
import os
import re
import sys
import threading
import time
import tkinter as tk
import tkinter.font

from macro import Data

VERSION = "2.0.1"

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
        self.games_scrollframe.pack(fill=tk.BOTH, expand=True)

class RobloxFrame:
    def __new__(self, master, macro):
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

        macro.add_data_callback(add_text)

        # LEFT SIDE

        info_frame = tk.Frame(frame, width=240)
        info_frame.pack_propagate(False)
        info_frame.pack(padx=5, pady=5, side=tk.LEFT, fill=tk.Y)

        tk.Label(info_frame, text=macro.roblox.get_name(), font=(FONT, 16)).pack(side=tk.TOP, pady=(10, 0))

        info_frame_bottom = tk.Frame(info_frame)
        info_frame_bottom.pack(padx=5, pady=5, fill=tk.X, side=tk.BOTTOM)

        enabled_frame = tk.Frame(info_frame_bottom)
        enabled_frame.pack(fill=tk.X, side=tk.TOP)

        enabled_var = tk.IntVar(value=macro.get_enabled())

        enabled_var.trace_add("write", lambda *e: macro.set_enabled(bool(enabled_var.get())))

        tk.Label(enabled_frame, text="Enabled") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N)
        tk.Checkbutton(enabled_frame, variable=enabled_var) \
            .pack(side=tk.RIGHT, anchor=tk.W, expand=True)

        lite_mode_frame = tk.Frame(info_frame_bottom)
        lite_mode_frame.pack(fill=tk.X, side=tk.TOP)

        lite_mode_var = tk.IntVar(value=macro.get_lite_mode())

        lite_mode_var.trace_add("write", lambda *e: macro.set_lite_mode(bool(lite_mode_var.get())))

        tk.Label(lite_mode_frame, text="Lite mode") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N)
        tk.Checkbutton(lite_mode_frame, variable=lite_mode_var) \
            .pack(side=tk.RIGHT, anchor=tk.W, expand=True)
    
        server_frame = tk.Frame(info_frame_bottom)
        server_frame.pack(fill=tk.X, side=tk.TOP)

        server_url_var = tk.StringVar(value=f"privateServerLinkCode={macro.get_server()}" if macro.get_server() else "")

        tk.Label(server_frame, text="Server url:") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N, padx=(0, 5))
        server_url_entry = tk.Entry(server_frame, textvariable=server_url_var, highlightthickness=2)
        server_url_entry.pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.N, expand=True)

        def write_verify_url(*e):
            code = re.search(".*privateServerLinkCode=([0-9]{32}).*", server_url_var.get())
            if code:
                server_url_entry.configure(highlightbackground="#54de01", highlightcolor="#54de01")

                macro.set_server(int(code.group(1)))
            else:
                server_url_entry.configure(highlightbackground="red", highlightcolor="red")

                macro.set_server(None)

        server_url_var.trace_add("write", write_verify_url)
        write_verify_url()

class ScrollFrame(tk.Frame):
    def __init__(self, master, *args, **kw):
        tk.Frame.__init__(self, master, *args, **kw)
        canvas = tk.Canvas(self)

        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(fill=tk.BOTH, expand=True)

        self.update()

        self.interior = tk.Frame(canvas)
        self.interior.bind("<Configure>", lambda _, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")))

        id = canvas.create_window((0, 0), window=self.interior, anchor=tk.NW, width=canvas.winfo_width()-2)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(id, width=e.width-2))

class PauseWindow:
    def __init__(self, master, config):
        self.root = tk.Toplevel(master, background="red")
        self.root.withdraw()

        self.config = config

        self.pause_events = []
        self.unpause_events = []

        self._timer = None

        self.setup()

    def setup(self):
        self.root.title("Re:Twisted - pop up")
        self.root.geometry("360x150")
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
        
    def unpause_all(self):
        [f() for f in self.unpause_events]

    def pause_all(self):
        [f() for f in self.pause_events]

    def start_timer(self):
        timer_mins = int(self.config.get(["resume timer"]) or 0)

        if not timer_mins:
            self.timer_text.config(text="")
            return
        
        timestamp = datetime.datetime.fromtimestamp(time.time() + timer_mins * 60).strftime("%H:%M")
        self.timer_text.config(text=f"If not closed will continue to reroll in {timer_mins} minutes ({timestamp})")

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
    
class ConfigWindow:
    class ConfigTemplate:
        def __init__(self):
            self.name = "TEMPLATE"

        def _create_gui(self, master):
            raise NotImplemented()
        
        def import_config(self, config, path=[]):
            raise NotImplemented()
        
        def export_config(self, config, path=[]):
            raise NotImplemented()

    class Group(ConfigTemplate):
        def __init__(self, name, childs):
            self.name = name
            self.childs = childs

        def _create_gui(self, master):
            tk.Label(master, text=self.name.capitalize()).pack(anchor=tk.W)

            submaster = tk.Frame(master)
            submaster.pack(anchor=tk.W, padx=(25, 0))

            for child in self.childs:
                child._create_gui(submaster)

        def import_config(self, config, path=[]):
            for child in self.childs:
                child.import_config(config, path + [self.name])

        def export_config(self, config, path=[]):
            for child in self.childs:
                child.export_config(config, path + [self.name])

    class EntryConfig(ConfigTemplate):
        def __init__(self, name, dtype, description, dvalue):
            self.name = name.lower()
            self.dtype = dtype
            self.description = description
            self.dvalue = dvalue

            self.inpt = tk.StringVar()
            self.inpt.trace_add("write", self._validate)

        def _validate(self, *_):
            string = self.inpt.get()

            match self.dtype():
                case int():
                    string = "".join([ch for ch in string if ch in "0123456789"])

                case float():
                    string = "".join([ch for ch in string if ch in ".0123456789"])
                    string = ".".join(string.split(".")[:2])

            self.inpt.set(string)

        def _create_gui(self, master):
            frame = tk.Frame(master)
            frame.pack(anchor=tk.W, pady=(0, 15))

            tk.Label(frame, text=self.name.capitalize()).pack(anchor=tk.W)

            tk.Label(frame, state=tk.DISABLED, text=self.description, 
                     font=(FONT, 10), justify=tk.LEFT) \
            .pack(anchor=tk.W)

            tk.Entry(frame, textvariable=self.inpt, width=50) \
                .pack(side=tk.LEFT, padx=(3, 0))
            
        def import_config(self, config, path=[]):
            try:
                config_value = self.dtype(config.get(path + [self.name]))
            except:
                config_value = self.dvalue

            self.inpt.set(config_value)

        def export_config(self, config, path=[]):
            try:
                config_value = self.dtype(self.inpt.get())
            except:
                config_value = self.dvalue

            config.set(path + [self.name], config_value)

    class ConditionConfig(ConfigTemplate):
        class ConditionGroup:
            class Condition:
                data_options = list(Data.FORMAT.keys())
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
                    data_format = Data.FORMAT[selected]

                    self.third_var.set("")

                    if data_format == str:
                        self.second_menu.configure(state="disabled")
                        self.second_var.set("==")
                    else:
                        self.second_menu.configure(state="active")

                def update_third(self, *args):
                    selected = self.first_var.get()
                    data_format = Data.FORMAT[selected]
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

        DESCRIPTION = "Bot stops if at least one group has all the conditions met within the group."

        def __init__(self, name):
            self.name = name

            self.master = None
            self._sublist = []

        def _create_gui(self, master):
            self.master = master

            description = tk.Label(self.master, state=tk.DISABLED, text=self.DESCRIPTION,
                                   font=(FONT, 10), justify=tk.CENTER)
            description.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

            description.config(wraplength=description.winfo_width())
            description.bind('<Configure>', lambda *_: description.config(wraplength=description.winfo_width()))

            tk.Button(self.master, text="Add group", command=lambda:
                      self.ConditionGroup(self.master, self._sublist)) \
                .pack(fill=tk.X, side=tk.BOTTOM)

        def import_config(self, config, path=[]):
            while self._sublist:
                self._sublist.pop().frame.destroy()         

            for groups in config.get(path + [self.name]):
                self.ConditionGroup(self.master, self._sublist) \
                    .import_config(groups)

        def export_config(self, config, path=[]):
            config_value = [group.export_config() for group in self._sublist]

            config.set(path + [self.name], config_value)

    def __init__(self, master, config) -> None:
        self.root= tk.Toplevel(master)
        self.root.withdraw()

        self.config = config

        self.left_config = [
            self.Group("webhook", [
                self.EntryConfig("url", str, "Webhook url where message will be sent on successful find.\nLeave empty for no message.", ""), 
                self.EntryConfig("role id", str, "Role which will be pinged in message.", ""),
                self.EntryConfig("user id", str, "User which will be pinged in message.", "")
            ]), 
            self.EntryConfig("timeout", int, "Maximum amount of time that the server can take to reroll.\nEntering 0 will disable this feature.", 75), 
            self.EntryConfig("resume timer", int, "Time in minutes after which the bot will continue rerolling automatically.\nEntering 0 will disable this feature.", 15)
        ]

        self.right_config = [
            self.ConditionConfig("conditions")
        ]

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
        
        # LEFT SIDE
        left_side = ScrollFrame(self.root)
        left_side.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_side.pack_propagate(False)
        
        for config_widget in self.left_config:
            config_widget._create_gui(left_side.interior)

        # RIGHT SIDE
        right_side = ScrollFrame(self.root)
        right_side.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        right_side.pack_propagate(False)

        for config_widget in self.right_config:
            config_widget._create_gui(right_side.interior)

    def open(self):
        for setting in self.left_config + self.right_config:
            setting.import_config(self.config)

        self.root.deiconify()

    def close(self):
        self.root.withdraw()

    def close_and_save(self):
        self.close()

        for setting in self.left_config + self.right_config:
            setting.export_config(self.config)
