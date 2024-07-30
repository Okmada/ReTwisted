import tkinter as tk
from typing import List

from config import ConfigManager
from constants import FONT, NAME
from gui.scrollframe import ScrollFrame
from macro.twistedmacro import TwistedData


class ConfigWindow:
    class ConfigTemplate:
        def __init__(self):
            self.name = "TEMPLATE"

        def _create_gui(self, master) -> None:
            raise NotImplementedError

        def import_config(self, config: ConfigManager, path=[]) -> None:
            raise NotImplementedError

        def export_config(self, config: ConfigManager, path=[]) -> None:
            raise NotImplementedError

    class Group(ConfigTemplate):
        def __init__(self, name: str, childs: List[object]):
            self.name = name.lower()
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
        def __init__(self, name, dtype, description):
            self.name = name.lower()
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
            frame = tk.Frame(master)
            frame.pack(anchor=tk.W, pady=(0, 15))

            tk.Label(frame, text=self.name.capitalize()).pack(anchor=tk.W)

            tk.Label(frame, state=tk.DISABLED, text=self.description,
                     font=(FONT, 10), justify=tk.LEFT) \
            .pack(anchor=tk.W)

            tk.Entry(frame, textvariable=self.inpt, width=50) \
                .pack(side=tk.LEFT, padx=(3, 0))

        def import_config(self, config, path=[]):
            config_value = config.get(path + [self.name])

            self.inpt.set(config_value)

        def export_config(self, config, path=[]):
            try:
                config_value = self.dtype(self.inpt.get())
            except:
                config_value = None

            config.set(path + [self.name], config_value)

    class BoolConfig(ConfigTemplate):
        options = ["Disabled", "Enabled"] # ["False", "True"]

        def __init__(self, name, description):
            self.name = name.lower()
            self.description = description

            self.inpt = tk.StringVar()

        def _create_gui(self, master):
            frame = tk.Frame(master)
            frame.pack(anchor=tk.W, pady=(0, 15))

            tk.Label(frame, text=self.name.capitalize()).pack(anchor=tk.W)

            tk.Label(frame, state=tk.DISABLED, text=self.description,
                     font=(FONT, 10), justify=tk.LEFT) \
                .pack(anchor=tk.W)

            tk.OptionMenu(frame, self.inpt, *self.options) \
                .pack(side=tk.LEFT, padx=(3, 0))

        def import_config(self, config, path=[]):
            config_value = int(config.get(path + [self.name]))

            self.inpt.set(self.options[config_value])

        def export_config(self, config, path=[]):
            config_value = self.options.index(self.inpt.get())

            config.set(path + [self.name], bool(config_value))

    class ConditionConfig(ConfigTemplate):
        class ConditionGroup:
            class Condition:
                data_options = list(TwistedData.FORMAT.keys())
                comparison_options = ["==", "<=", ">="]

                def __init__(self, master, superlist: List) -> None:
                    self.master = master

                    self.frame = tk.Frame(master, highlightbackground="black", highlightthickness=1)
                    self.frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

                    self._superlist = superlist
                    self._superlist.append(self)

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
                    data_format = TwistedData.FORMAT[selected]

                    self.third_var.set("")

                    if data_format == str:
                        self.second_menu.configure(state="disabled")
                        self.second_var.set("==")
                    else:
                        self.second_menu.configure(state="active")

                def update_third(self, *_) -> None:
                    selected = self.first_var.get()
                    data_format = TwistedData.FORMAT[selected]
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

            def __init__(self, master, superlist: List) -> None:
                self.master = master

                self.frame = tk.Frame(master, highlightbackground="black", highlightthickness=2)
                self.frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

                self._sublist = []

                self._superlist = superlist
                self._superlist.append(self)

                self._create_widgets()

            def _create_widgets(self) -> None:
                subframe = tk.Frame(self.frame)
                subframe.pack(fill=tk.BOTH, padx=5, pady=5)

                self.add_condition_button = tk.Button(subframe, text="Add condition", command=self.add_condition)
                self.add_condition_button.pack(fill=tk.X, side=tk.LEFT)

                self.delete_group_button = tk.Button(subframe, text="Delete group", command=self.delete_group)
                self.delete_group_button.pack(fill=tk.X, side=tk.RIGHT)

            def add_condition(self) -> None:
                self.Condition(self.frame, self._sublist)

            def delete_group(self) -> None:
                self.frame.destroy()
                self._superlist.remove(self)

            def import_config(self, config: List[List[str]]) -> None:
                for subconfig in config:
                    self.Condition(self.frame, self._sublist) \
                        .import_config(subconfig)

            def export_config(self) -> List[List[str]]:
                return [condintion.export_config() for condintion in self._sublist]

        DESCRIPTION = "Bot stops if at least one group has all the conditions met within the group."

        def __init__(self, name: str):
            self.name = name.lower()

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

    def __init__(self, master, config: ConfigManager) -> None:
        self.root= tk.Toplevel(master)
        self.root.withdraw()

        self.config = config

        self.left_config = [
            self.Group("webhook", [
                self.EntryConfig("url", str, "Webhook url where message will be sent on successful find.\nLeave empty for no message."),
                self.BoolConfig("share link", "Adds a hyperlink to the server that has been rolled.\nWorks only for VIP servers."),
                self.EntryConfig("role id", str, "Role which will be pinged in message."),
                self.EntryConfig("user id", str, "User which will be pinged in message.")
            ]),
            self.EntryConfig("timeout", int, "Maximum amount of time that the server can take to reroll.\nEntering 0 will disable this feature."),
            self.EntryConfig("resume timer", int, "Time in minutes after which the bot will continue rerolling automatically.\nEntering 0 will disable this feature."),
            self.BoolConfig("save data", "Exports data from every roll to csv file"),
            self.BoolConfig("bloxstrap", "Use Bloxstrap instead of Roblox Player, if available."),
        ]

        self.right_config = [
            self.ConditionConfig("conditions")
        ]

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

        for config_widget in self.left_config:
            config_widget._create_gui(left_side.interior)

        # RIGHT SIDE
        right_side = ScrollFrame(self.root)
        right_side.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        right_side.pack_propagate(False)

        for config_widget in self.right_config:
            config_widget._create_gui(right_side.interior)

    def open(self) -> None:
        for setting in self.left_config + self.right_config:
            setting.import_config(self.config)

        self.root.deiconify()

    def close(self) -> None:
        self.root.withdraw()

    def close_and_save(self) -> None:
        self.close()

        for setting in self.left_config + self.right_config:
            setting.export_config(self.config)
