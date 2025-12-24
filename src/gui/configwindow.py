import re
import tkinter as tk
from typing import Dict, List

from config import ConfigManager
from constants import FONT, NAME
from gui.scrollframe import ScrollFrame
from macro.macros import DefaultMacro, Macros


class ConfigWindow:
    class ConfigTemplate:
        def __init__(self):
            self.frame = None

        def _create_gui(self, master) -> None:
            self.frame = tk.Frame(master)
            self.frame.pack(anchor=tk.W, fill=tk.X)

        def import_config(self, config) -> None:
            raise NotImplementedError

        def export_config(self) -> object:
            raise NotImplementedError

    class Group(ConfigTemplate):
        def __init__(self, childs: Dict[str, object], offset=True):
            super().__init__()
            
            self.childs = childs
            self.offset = offset

        def _create_gui(self, master):
            # SPECIAL FRAME

            self.frame = tk.Frame(master)
            self.frame.pack(anchor=tk.W, padx=(25 if self.offset else 0, 0), fill=tk.X)

            for name, child in self.childs.items():
                tk.Label(self.frame, text=name.capitalize()) \
                    .pack(anchor=tk.W)
                
                child._create_gui(self.frame)

        def import_config(self, config):
            for name, child in self.childs.items():
                if name in config:
                    child.import_config(config[name])

        def export_config(self):
            return { name: child.export_config() for name, child in self.childs.items() }

    class EntryConfig(ConfigTemplate):
        def __init__(self, dtype, description):
            super().__init__()

            self.entry = None
            
            self.dtype = dtype
            self.description = description

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
            super()._create_gui(master)

            tk.Label(self.frame, state=tk.DISABLED, text=self.description,
                     font=(FONT, 10), justify=tk.LEFT) \
            .pack(anchor=tk.W)

            self.entry = tk.Entry(self.frame, textvariable=self.inpt, width=50)
            self.entry.pack(side=tk.LEFT, padx=(3, 0))

        def import_config(self, config):
            self.inpt.set(config)

        def export_config(self):
            try:
                return self.dtype(self.inpt.get())
            except Exception:
                return None

    class BoolConfig(ConfigTemplate):
        options = ["Disabled", "Enabled"] # ["False", "True"]

        def __init__(self, description):
            super().__init__()

            self.description = description

            self.inpt = tk.StringVar()

        def _create_gui(self, master):
            super()._create_gui(master)

            tk.Label(self.frame, state=tk.DISABLED, text=self.description,
                     font=(FONT, 10), justify=tk.LEFT) \
                .pack(anchor=tk.W)

            tk.OptionMenu(self.frame, self.inpt, *self.options) \
                .pack(side=tk.LEFT, padx=(3, 0))

        def import_config(self, config):
            self.inpt.set(self.options[int(config)])

        def export_config(self):
            return bool(self.options.index(self.inpt.get()))
        
    class SelectorGroup(ConfigTemplate):
        def __init__(self, childs: Dict[str, object], default=None):
            super().__init__()

            if default is not None:
                assert default in childs

            self.childs = childs

            self.inpt = tk.StringVar(value=default)
            self.inpt.trace_add("write", self.change)

            self.current = default
            self.config = {}

        def _create_gui(self, master):
            super()._create_gui(master)
            
            tk.OptionMenu(self.frame, self.inpt, *self.childs.keys()) \
                .pack(fill=tk.X, side=tk.TOP)
            
            self.childs_gui = {}
            for key, child in self.childs.items():
                child_frame = tk.Frame(self.frame)
                child._create_gui(child_frame)
                self.childs_gui[key] = child_frame

            self.change()

        def change(self, *_):
            if self.current is not None:
                self.childs_gui[self.current].pack_forget()

            self.current = self.inpt.get()

            if self.current in self.childs_gui:
                self.childs_gui[self.current].pack(fill=tk.X, side=tk.TOP)
            else:
                self.current = None


        def import_config(self, config):
            for name, child in self.childs.items():
                if name.lower() in config:
                    child.import_config(config[name.lower()])

        def export_config(self):
            return { name.lower(): child.export_config() for name, child in self.childs.items() }
        
    class ServerConfig(EntryConfig):
        GREEN = "#54de01"
        RED = "red"

        def __init__(self):
            super().__init__(str, "Enter url of server you wish to roll")

        def _create_gui(self, master):
            super()._create_gui(master)

            self.entry.configure(highlightthickness=2, highlightbackground=self.RED, highlightcolor=self.RED)

        def _parse_url(self) -> tuple[str]:
            linkCode = re.search(".*privateServerLinkCode=([0-9]{32}).*", self.inpt.get())
            code = re.search(".*code=([a-z0-9]{32}).*", self.inpt.get())
            return (linkCode, code)

        def _validate(self, *_):
            linkCode, code = self._parse_url()

            if code and self.frame is not None:
                popup = tk.Toplevel(self.frame)
                popup.resizable(False, False)
                popup.title("Wrong link detected!")
                tk.Label(popup, justify=tk.LEFT, text="An incorrect link has been detected. Follow these steps to obtain the correct link:\n\n1) Open the current link in a browser where you are logged into Roblox.\n2) Wait a few seconds for Roblox to redirect and launch.\n3) Copy the link from the address bar and paste it in.").pack(padx=10, pady=10)
                self.inpt.set("")
                popup.grab_set()
                popup.focus()

            if self.entry is not None:
                color = self.GREEN if linkCode else self.RED
                self.entry.configure(highlightbackground=color, highlightcolor=color)

        def import_config(self, config):
            super().import_config(f"privateServerLinkCode={config}" if config else "")

            self._validate()

        def export_config(self):
            linkCode, _ = self._parse_url()
            return str(linkCode.group(1)) if linkCode else ""

    class ConditionConfig(ConfigTemplate):
        class ConditionGroup:
            class Condition:
                comparison_options = ["==", "<=", ">="]

                def __init__(self, master, superlist: List, macro: str) -> None:
                    self.master = master

                    self.frame = tk.Frame(master, highlightbackground="black", highlightthickness=1)
                    self.frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

                    self._superlist = superlist
                    self._superlist.append(self)

                    self.data_format = Macros[macro].Data.FORMAT
                    self.data_options = list(self.data_format.keys())

                    self._create_widgets()

                def _create_widgets(self) -> None:
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

                def update_first(self, *_) -> None:
                    selected = self.first_var.get()
                    data_format = self.data_format[selected]

                    self.third_var.set("")

                    if data_format == str:
                        self.second_menu.configure(state="disabled")
                        self.second_var.set("==")
                    else:
                        self.second_menu.configure(state="active")

                def update_third(self, *_) -> None:
                    selected = self.first_var.get()
                    data_format = self.data_format[selected]
                    input_value = self.third_var.get()

                    if data_format == str:
                        self.third_var.set(input_value.upper())
                    elif data_format == int:
                        self.third_var.set(''.join(c for c in input_value if c in "0123456789"))
                    elif data_format == float:
                        self.third_var.set(''.join(c for c in input_value if c in ".0123456789"))

                def delete(self) -> None:
                    self.frame.destroy()
                    self._superlist.remove(self)

                def import_config(self, config: List[str]) -> None:
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

                def export_config(self) -> List[str]:
                    return [self.first_var.get(), self.second_var.get(), self.third_var.get()]

            def __init__(self, master, superlist: List, macro: str) -> None:
                self.master = master

                self.frame = tk.Frame(master, highlightbackground="black", highlightthickness=2)
                self.frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

                self._sublist = []

                self._superlist = superlist
                self._superlist.append(self)

                self.macro = macro

                self._create_widgets()

            def _create_widgets(self) -> None:
                subframe = tk.Frame(self.frame)
                subframe.pack(fill=tk.BOTH, padx=5, pady=5)

                self.add_condition_button = tk.Button(subframe, text="Add condition", command=self.add_condition)
                self.add_condition_button.pack(fill=tk.X, side=tk.LEFT)

                self.delete_group_button = tk.Button(subframe, text="Delete group", command=self.delete_group)
                self.delete_group_button.pack(fill=tk.X, side=tk.RIGHT)

            def add_condition(self) -> None:
                self.Condition(self.frame, self._sublist, self.macro)

            def delete_group(self) -> None:
                self.frame.destroy()
                self._superlist.remove(self)

            def import_config(self, config: List[List[str]]) -> None:
                for subconfig in config:
                    self.Condition(self.frame, self._sublist, self.macro) \
                        .import_config(subconfig)

            def export_config(self) -> List[List[str]]:
                return [condintion.export_config() for condintion in self._sublist]

        DESCRIPTION = "Bot stops if at least one group has all the conditions met within the group."

        def __init__(self, macro: str):
            super().__init__()

            self.macro = macro

            self._sublist = []

        def _create_gui(self, master):
            super()._create_gui(master)

            description = tk.Label(self.frame, state=tk.DISABLED, text=self.DESCRIPTION,
                                   font=(FONT, 10), justify=tk.CENTER)
            description.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

            description.config(wraplength=description.winfo_width())
            description.bind('<Configure>', lambda *_: description.config(wraplength=description.winfo_width()))

            tk.Button(self.frame, text="Add group", command=lambda:
                      self.ConditionGroup(self.frame, self._sublist, self.macro)) \
                .pack(fill=tk.X, side=tk.BOTTOM)
            
        def clear(self):
            while self._sublist:
                self._sublist.pop().frame.destroy()

        def import_config(self, config):
            self.clear()
            for group in config:
                    self.ConditionGroup(self.frame, self._sublist, self.macro) \
                        .import_config(group)


        def export_config(self):
            return [group.export_config() for group in self._sublist]

    def __init__(self, master) -> None:
        self.root= tk.Toplevel(master)
        self.root.withdraw()

        self.left_config = self.Group({
            "webhook": self.Group({
                "url": self.EntryConfig(str, "Webhook url where message will be sent on successful find.\nLeave empty for no message."),
                "share link": self.BoolConfig("Adds a hyperlink to the server that has been rolled.\nWorks only for VIP servers."),
                "role id": self.EntryConfig(str, "Role which will be pinged in message."),
                "user id": self.EntryConfig(str, "User which will be pinged in message.")
            }),
            "leave after roll": self.Group({
                "enabled": self.BoolConfig("Automatically leaves the game after a successful roll."),
                "time": self.EntryConfig(int, "Time to stay in the home screen (seconds).")
            }),
            "timeout": self.EntryConfig(int, "Maximum amount of time that the server can take to reroll.\nEntering 0 will disable this feature."),
            "resume timer": self.EntryConfig(int, "Time in minutes after which the bot will continue rerolling automatically.\nEntering 0 will disable this feature."),
            "save data": self.BoolConfig("Exports data from every roll to csv file"),
            "roblox player launcher override": self.EntryConfig(str, "Define exact path of Roblox Player or other 3rd-party launcher (.exe / .lnk).\nWARNING: provided file will be executed!"),
        }, offset=False)

        self.right_config = self.SelectorGroup({
            macro: self.Group({
                "server": self.Group({
                    # "microsoft roblox": self.ServerConfig(),
                    "roblox player": self.ServerConfig(),
                }),
                "conditions": self.ConditionConfig(macro),
            }, offset=False)
        for macro in Macros}, default=DefaultMacro)

        self._setup()

    def _setup(self) -> None:
        self.root.title(f"{NAME} - config")
        self.root.geometry("1000x600")
        self.root.resizable(True, True)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Button(bottom_frame, text="Save", command=self.close_and_save) \
            .pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

        tk.Button(bottom_frame, text="Close", command=self.close) \
            .pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5, pady=5)

        # LEFT SIDE
        left_side = ScrollFrame(self.root)
        left_side.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_side.pack_propagate(False)

        self.left_config._create_gui(left_side.interior)

        # RIGHT SIDE
        right_side = ScrollFrame(self.root)
        right_side.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        right_side.pack_propagate(False)

        self.right_config._create_gui(right_side.interior)

    def open(self) -> None:
        self.left_config.import_config(ConfigManager().get([]))
        self.right_config.import_config(ConfigManager().get(["macros"]))

        self.root.deiconify()

    def close(self) -> None:
        self.root.withdraw()

    def close_and_save(self) -> None:
        self.close()

        ConfigManager().set([], self.left_config.export_config())
        ConfigManager().set(["macros"], self.right_config.export_config())
