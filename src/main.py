import tkinter as tk

import gui
from config import Config
from controller import Controller
from discord import Webhook
from macro import Macro
from roblox import Roblox

print("/!\\ DO NOT CLOSE THIS CONSOLE /!\\")

config = Config()
webhook = Webhook(config)

# CREATE ROOT AND MAIN GUI
root = tk.Tk()

gui_main = gui.Main(root)

gui_config = gui.ConfigWindow(root, config)
gui_main.config_events.append(gui_config.open)

gui_pause = gui.PauseWindow(root)
gui_pause.pause_events = gui_main.pause_events
gui_pause.unpause_events = gui_main.unpause_events
gui_main.unpause_events.append(gui_pause.close)

# CREATE CONTROLLER
controller = Controller()
gui_main.pause_events.append(controller.pause)
gui_main.unpause_events.append(controller.unpause)

# CREATE ROBLOX GAMES
for roblox_type in Roblox.CLASS_NAMES.keys():
    roblox_game = Roblox(roblox_type)

    macro = Macro(roblox_game, controller, config, webhook)
    macro.add_pause_callback(lambda *_: gui_pause.open_and_pause())

    gui_main.pause_events.append(macro.pause)
    gui_main.unpause_events.append(macro.unpause)

    gui.RobloxFrame(gui_main.games_scrollframe, macro)

root.mainloop()

# TODO
# sys.stdout = TextRedirector()
# class TextRedirector(object):
#     def __init__(self, widget, tag="stdout"):
#         self.widget = widget
#         self.tag = tag

#     def write(self, string):
#         self.widget.configure(state="normal")
#         self.widget.insert("end", string, (self.tag,))
#         self.widget.configure(state="disabled")