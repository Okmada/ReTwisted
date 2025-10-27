import logging
import sys
import tkinter as tk

from config import ConfigManager
from constants import NAME, VERSION
from controller import Controller
from datalogger import DataLogger
from discord import Webhook
from gui import configwindow, mainwindow, pausewindow, robloxframe
from macro.macrohandler import MacroHandler
from odr import ODR
from roblox import Roblox, RobloxTypes

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

logging.info(f"{NAME} v{VERSION} started up")

# START CONFIG AND INITIALIZE WEBHOOK AND DATA LOGGER
ConfigManager()
webhook = Webhook()
data_logger = DataLogger()

# CREATE ROOT AND MAIN GUI
root = tk.Tk()

gui_main = mainwindow.MainWindow(root)

gui_config = configwindow.ConfigWindow(root)
gui_main.config_events.append(gui_config.open)

gui_pause = pausewindow.PauseWindow(root)
gui_pause.pause_events = gui_main.pause_events
gui_pause.unpause_events = gui_main.unpause_events
gui_main.unpause_events.append(gui_pause.close)

# INITIALIZE ODR
ODR().load()
ODR().train()

# CREATE CONTROLLER
controller = Controller()
gui_main.pause_events.append(controller.pause)
gui_main.unpause_events.append(controller.unpause)

# CREATE ROBLOX GAMES
for roblox_type in (RobloxTypes.WINDOWSCLIENT, ):
    roblox_game = Roblox(roblox_type)

    macro = MacroHandler(roblox_game, webhook)
    macro.add_pause_callback(lambda *_: gui_pause.open())

    gui_main.pause_events.append(macro.pause)
    gui_main.unpause_events.append(macro.unpause)

    robloxframe.RobloxFrame(gui_main.games_scrollframe.interior, macro)

root.mainloop()
