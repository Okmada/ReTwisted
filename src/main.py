import logging
import sys
import tkinter as tk

import gui
from config import Config
from controller import Controller
from discord import Webhook
from macro import Macro
from roblox import Roblox
from datalogger import DataLogger

# SETUP LOGGING
log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
root_logger = logging.getLogger()
root_logger.setLevel(logging.NOTSET)

file_handler = logging.FileHandler("latest.log", "a")
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logging.info("ReTwisted started up")

# START CONFIG AND INITIALIZE WEBHOOK AND DATA LOGGER
config = Config()
webhook = Webhook(config)
data_logger = DataLogger(config)

# CREATE ROOT AND MAIN GUI
root = tk.Tk()

gui_main = gui.Main(root)

gui_config = gui.ConfigWindow(root, config)
gui_main.config_events.append(gui_config.open)

gui_pause = gui.PauseWindow(root, config)
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
    macro.add_pause_callback(lambda *_: gui_pause.open())
    macro.add_data_callback(data_logger.append)

    gui_main.pause_events.append(macro.pause)
    gui_main.unpause_events.append(macro.unpause)

    gui.RobloxFrame(gui_main.games_scrollframe.interior, macro)

root.mainloop()
