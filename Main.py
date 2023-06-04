from tkinter import font
from ctypes import windll
from time import sleep
from requests import post
import win32gui
import win32ui
import win32con
import numpy as np
import cv2
import threading
import pytesseract
import pydirectinput
import time
import tkinter as tk
import json
import sys
import os

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

W, H = 975, 850
FOLDER = "assets/"

FRIEND = cv2.imread(resource_path(FOLDER + "friend.png"))
JOIN_FRIEND = cv2.imread(resource_path(FOLDER + "join-friend.png"))

JOIN_BTN = cv2.imread(resource_path(FOLDER + "join-button.png"))

PLAY = cv2.imread(resource_path(FOLDER + "play.png"))
MENU = cv2.imread(resource_path(FOLDER + "menu-icon.png"))
WEATHER = cv2.imread(resource_path(FOLDER + "weather-icon.png"))

CAPE_ONLY = cv2.imread(resource_path(FOLDER + "cape-only.png"))
CAPE = cv2.imread(resource_path(FOLDER + "cape.png"))
CAPE_MASK = cv2.imread(resource_path(FOLDER + "cape-mask.png"))

TWISTED = cv2.imread(resource_path(FOLDER + "twisted.png"))

DESKTOP = win32gui.GetDesktopWindow()

class TOOLS:
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)

    @staticmethod
    def cropXYWH(image, x, y, w, h):
        ih, iw = image.shape[:2]
        return image[TOOLS.clamp(y, 0, ih - h):TOOLS.clamp(y + h, h, ih),
                TOOLS.clamp(x, 0, iw - w):TOOLS.clamp(x + w, w, iw)]
    
    @staticmethod
    def findPos(template, image, threshold=.1):
        res = cv2.matchTemplate(image, template, cv2.TM_SQDIFF_NORMED)
        lerror, herror, loc, _ = cv2.minMaxLoc(res)
        x, y = loc

        h, w = template.shape[:2]
        return lerror <= threshold, x + w//2, y + h//2
    
    def findMultiplePos(template, image, threshold=.9):
        res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)

        h, w = template.shape[:2]
        return [(pos[0] + w//2, pos[1] + h//2) for pos in zip(*loc[::-1])]
    
class IHANDLER(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = "Input Handler"

        self.eventsQueue = []
        self.event = threading.Event()

        self.paused = threading.Event()
        self.statusCallback = None

        self.start()

    def pause(self):
        self.statusCallback("Status - Paused")
        self.paused.clear()

    def unpause(self):
        self.statusCallback("Status - Running")
        self.paused.set()

    @staticmethod
    def focuswindow(window):
        pydirectinput.keyDown("alt")
        try:
            win32gui.SetForegroundWindow(window)
        finally:
            pydirectinput.keyUp("alt")

    @staticmethod
    def click(win, x, y):
        IHANDLER.focuswindow(win)

        mx, my = win32gui.GetWindowRect(win)[:2]

        match win32gui.GetClassName(win):
            case "WINDOWSCLIENT":
                IHANDLER.focuswindow(DESKTOP)
                pydirectinput.doubleClick(mx + x, my + y)
            case "ApplicationFrameWindow":
                pydirectinput.leftClick(mx + x, my + y)

    def qClick(self, win, x, y):
        self.eventsQueue.append(lambda: self.click(win, x, y))
        self.event.set()

    @staticmethod
    def pressKey(win, key, time=.25):
        IHANDLER.focuswindow(win)

        pydirectinput.keyDown(key)

        sleep(time)

        pydirectinput.keyUp(key)

    def qPressKey(self, win, key):
        self.eventsQueue.append(lambda: self.pressKey(win, key))
        self.event.set()

    def run(self):
        while True:
            self.event.wait()
            self.paused.wait()

            if self.eventsQueue:
                self.eventsQueue.pop(0)()
            else:
                self.event.clear()

class GAME(threading.Thread):
    CLASSNAMES = {
        "WINDOWSCLIENT": "Roblox Player",
        "ApplicationFrameWindow": "Microsoft Roblox"
    }

    def __init__(self, win, handler, config, dataCallback, server=0):
        threading.Thread.__init__(self)

        self.win = win
        self.name = win32gui.GetClassName(self.win)
        self.handler = handler
        self.server = server
        self.config = config

        self.dataCallback = dataCallback
        self.historyTextCallback = None

        self.history = []
        self.rerollsSGS = 0

        self.start()

    def crashDetection(self):
        match self.name:
            case "WINDOWSCLIENT":
                if (win := win32gui.FindWindow(None, "Roblox Crash")) == 0:
                    return False
                win32gui.PostMessage(win, win32con.WM_CLOSE, 0, 0)

            case "ApplicationFrameWindow":
                if win32gui.IsWindow(self.win):
                    return False
                
            case _:
                return None
                            
        if path := self.config(["paths", self.getName().lower()]):
            os.startfile(path)

        while (newWin := win32gui.FindWindow(self.name, "Roblox")) in [self.win, 0]:
            sleep(.1)
        self.win = newWin

        self.findAndClick(TWISTED, threshold=0.005)
        self.run()

    def getName(self, masked=True):
        if self.name in self.CLASSNAMES.keys() and masked:
            return self.CLASSNAMES[self.name]
        else:
            return self.name

    def setServer(self, server):
        self.server = server

    def resize(self):
        left, top, right, bot = win32gui.GetWindowRect(self.win)
        w, h = right - left, bot - top
        if w != W or h != H:
            win32gui.MoveWindow(self.win, left, top, W, H, True)

    def getscr(self):
        self.crashDetection()

        self.resize()

        left, top, right, bot = win32gui.GetWindowRect(self.win)
        w, h = right - left, bot - top

        hwndDC = win32gui.GetWindowDC(self.win)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

        saveDC.SelectObject(saveBitMap)

        windll.user32.PrintWindow(self.win, saveDC.GetSafeHdc(), 2)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        img = np.frombuffer(bmpstr, dtype=np.uint8)
        img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
        img = img[:,:,:3]

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(self.win, hwndDC)

        return img.astype(dtype=np.uint8)
    
    def findCoords(self, image, interval=.25, threshold=.1):
        ox, oy = None, None
        while True:
            success, x, y = TOOLS.findPos(image, self.getscr(), threshold=threshold)
            
            if success:
                if ox == x and oy == y:
                    return x, y
                ox, oy = x, y
            else:
                ox, oy = None, None
                        
            sleep(interval)
    
    def findAndClick(self, images, threshold=.1):
        if type(images) is not list:
            images = [images]

        for image in images:
            x, y = self.findCoords(image, threshold=threshold)

            self.handler.qClick(self.win, x, y)
    
    def openServers(self):
        self.findAndClick([FRIEND, JOIN_FRIEND])

        while not TOOLS.findPos(JOIN_BTN, self.getscr(), threshold=0.005)[0]:
            sleep(.25)

    def joinServer(self, n):
        servers = TOOLS.findMultiplePos(JOIN_BTN, self.getscr())
        pos = servers[TOOLS.clamp(n, 0, len(servers) - 1)]

        self.handler.qClick(self.win, pos[0], pos[1])

    def quitGame(self):
        self.handler.qPressKey(self.win, "esc")

        self.handler.qPressKey(self.win, "l")

        self.handler.qPressKey(self.win, "enter")

    def restartGame(self):
        self.quitGame()
        self.openServers()
        self.joinServer(self.server)

    def getInfo(self):
        self.findAndClick([PLAY, MENU, WEATHER])

        self.findCoords(CAPE_ONLY)

        scr = self.getscr()
        _, _, loc, _ = cv2.minMaxLoc(cv2.matchTemplate(scr, CAPE, cv2.TM_SQDIFF_NORMED, mask=CAPE_MASK))
        cropped = TOOLS.cropXYWH(scr, loc[0], loc[1], CAPE.shape[1], CAPE.shape[0])
        text = pytesseract.image_to_string(cropped).strip()
        return [int("".join(l)) for l in [[ch for ch in t if ch.isdigit()] for t in text.split(" ")] if len(l)][1]  


    def run(self):
        timebeg = time.time()
        self.openServers()
        self.joinServer(self.server)
        while True:
            cape = self.getInfo()

            timeend = time.time()
            self.history.append([timeend - timebeg, cape])
            self.historyTextCallback(timeend, cape)
            self.rerollsSGS += 1

            self.dataCallback(self, cape)

            timebeg = time.time()
            self.restartGame()

class DiscordWebHook:
    def send(url, pingId, stats):
        if not url:
            return
        
        post(url, json={
            "username": "Re:Twisted bot",
            "content" : f"<@{pingId}>" if pingId else "",
            "embeds": [{
                "title" : "Winds are picking up on speed :cloud_tornado:",
                "description": f"Cape: **{stats}** J/kg"
            }]
        })

class GUI:
    class PausePopUP:
        def __init__(self, parent):
            self.root = tk.Toplevel(parent)
            self.root.withdraw()

            self.continueCallback = None

            self.setup()

        def setup(self):
            self.root.title("Re:Twisted - pop up")
            self.root.geometry("350x150")
            self.root.resizable(False, False)

            self.root.protocol("WM_DELETE_WINDOW", self.close)
            
            frame = tk.Frame(self.root)
            frame.pack(padx=15, pady=15, fill=tk.BOTH, expand=True)

            tk.Label(frame, text="Good server have been found", font=(None, 16)).pack()
            tk.Label(frame, text="Do you wish to continue", font=(None, 14)).pack()

            buttons = tk.Frame(frame)
            buttons.pack(side=tk.BOTTOM, fill=tk.X, expand=True)

            tk.Button(buttons, text="Yes", font=(None, 14), command=self.continueAndClose) \
                .pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            tk.Button(buttons, text="No", font=(None, 14), command=self.close) \
                .pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)
            
        def continueAndClose(self):
            self.continueCallback()
            self.close()

        def open(self):
            self.root.deiconify()

        def close(self):
            self.root.withdraw()

    class GameFrame:
        def __init__(self, parent, game):
            self.game = game

            self.frame = tk.Frame(parent, width=470, height=250, background="#aaa")
            self.frame.pack(padx=5, pady=5)
            self.frame.pack_propagate(False)

            self.setup()

            game.historyTextCallback = self.appendToHistory

        def setup(self):
            history_frame = tk.Frame(self.frame, width=210)
            history_frame.pack_propagate(False)
            history_frame.pack(padx=5, pady=5, side=tk.RIGHT, fill=tk.Y)

            self.historyText = tk.Text(history_frame, state=tk.DISABLED)
            scrollbar = tk.Scrollbar(history_frame, command=self.historyText.yview)
            self.historyText['yscrollcommand'] = scrollbar.set

            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.historyText.pack(expand=True, fill=tk.X)

            self.game.historyUpdate = self.appendToHistory

            info_frame = tk.Frame(self.frame, width=500)
            info_frame.pack_propagate(False)
            info_frame.pack(padx=5, pady=5, side=tk.LEFT, fill=tk.Y)

            tk.Label(info_frame, text=self.game.getName()).pack(side=tk.TOP, padx=10, pady=10)

            info_frame_bottom = tk.Frame(info_frame)
            info_frame_bottom.pack(padx=5, pady=5, fill=tk.X, side=tk.BOTTOM)

            inte = tk.StringVar(value=0)
            def validate():
                num = max(0, int("0" + "".join([n for n in inte.get() if n.isnumeric()])))
                inte.set(num)
                self.game.setServer(num)
                return True
            inte.trace_add("write", lambda *e: validate())

            # tk.Label(info_frame_bottom, text="Server settings") \
            #     .pack(fill=tk.X, side=tk.TOP, anchor=tk.N, pady=5, padx=5, expand=True)
            
            server_frame = tk.Frame(info_frame_bottom)
            server_frame.pack(fill=tk.X, side=tk.TOP)
            tk.Label(server_frame, text="Server:") \
                .pack(fill=tk.X, side=tk.LEFT, anchor=tk.N, pady=5, padx=5, expand=True)
            tk.Entry(server_frame, textvariable=inte) \
                .pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.N, pady=5, padx=5, expand=True)
            
            tk.Label(info_frame_bottom, state=tk.DISABLED, text="Which server (from top) will be selected", font=(None, 10)) \
                .pack(fill=tk.X, side=tk.TOP)

        def appendToHistory(self, timestamp, num):
            self.historyText.configure(state=tk.NORMAL)
            self.historyText.insert("1.0", f"{time.strftime('%H:%M:%S', time.localtime(timestamp))} - {num} J/kg\n")
            self.historyText.configure(state=tk.DISABLED)

        def destroy(self):
            self.frame.pack_forget()

    def __init__(self):
        self.root = tk.Tk()

        self.config = CONFIG(self.root)
        self.popup = self.PausePopUP(self.root)
        self.ihandler = IHANDLER()

        self.popup.continueCallback = self.ihandler.unpause

        self.setup()

        self.games = []
        for className in GAME.CLASSNAMES.keys():
            if (win := win32gui.FindWindow(className, "Roblox")) != 0:
                self.newGame(win)

        self.updateHisotry()

        self.root.mainloop()

        os._exit(1)

    def newGame(self, win):
        game = GAME(win, self.ihandler, self.config.getSetting, self.handleData)

        self.games.append(game)
        self.GameFrame(self.right_side_SF, game)

    def handleData(self, game, num):
        if num >= self.config.getSetting(["cape", "highest"]) or num <= self.config.getSetting(["cape", "lowest"]):
            self.popup.open()
            self.ihandler.pause()
            DiscordWebHook.send(self.config.getSetting(["webhook", "url"]), 
                                self.config.getSetting(["webhook", "ping-id"]), 0)
            game.rerollsSGS = 0

        self.updateHisotry()
    
    def updateHisotry(self):
        history = [stat for game in self.games for stat in game.history]
        timeHistory = [time for time, cape in history]
        capeHistory = [cape for time, cape in history]

        for recordType, command, label in self.recordsUpdateCallbacks:
            label.config(text=f"{recordType}: {command(timeHistory, capeHistory, self.games)}")

    def setup(self):
        self.root.title("Re:Twisted")
        self.root.geometry("800x500")
        self.root.resizable(False, True)
        self.root.iconphoto(True, tk.PhotoImage(file=resource_path("icon.png")))

        self.root.defaultFont = font.nametofont("TkDefaultFont")
        self.root.defaultFont.configure(family="Comic Sans MS", size=18)

        self.lbg = "#ccc"
        self.left_side = tk.Frame(self.root, width=300, background=self.lbg)
        self.left_side.pack(side=tk.LEFT, fill=tk.BOTH)
        self.left_side.pack_propagate(False)

        self.right_side = tk.Frame(self.root, width=500)
        self.right_side.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.right_side.pack_propagate(False)


        tk.Label(self.left_side, text="Re:Twisted - alpha", font=(None, 20), background=self.lbg) \
            .pack(side=tk.TOP, pady=(0, 15))
        
        status = tk.Label(self.left_side, text="Status - Paused", background=self.lbg)
        status.pack(side=tk.TOP)
        self.ihandler.statusCallback = lambda text: status.config(text=text)

        server_buttons = tk.Frame(self.left_side, background=self.lbg)
        server_buttons.pack( fill=tk.X, side=tk.TOP)
        tk.Button(server_buttons, text="Start", command=self.ihandler.unpause) \
            .pack(fill=tk.X, side=tk.LEFT, anchor=tk.N, pady=5, padx=5, expand=True)
        tk.Button(server_buttons, text="Pause", command=self.ihandler.pause) \
            .pack(fill=tk.X, side=tk.RIGHT, anchor=tk.N, pady=5, padx=5, expand=True)

        tk.Button(self.left_side, text="Settings", command= self.config.open) \
            .pack(fill=tk.X, side=tk.TOP, pady=5, padx=5)

        tk.Label(self.left_side, text="Records", background=self.lbg) \
            .pack(side=tk.TOP)
        
        left_sf_canvas = tk.Canvas(self.left_side)
        self.left_side_SF = tk.Frame(left_sf_canvas)

        scrollbar = tk.Scrollbar(self.left_side, orient=tk.VERTICAL, command=left_sf_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5, padx=(0, 5))
        left_sf_canvas.configure(yscrollcommand=scrollbar.set)

        left_sf_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=(5, 0))
        left_sf_canvas.create_window((0,0), window=self.left_side_SF, anchor=tk.NW)

        self.left_side_SF.bind("<Configure>", \
            lambda event, canvas=left_sf_canvas: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self.recordsUpdateCallbacks = []        
        for recordType, command in [["Highest cape", lambda timeHistory, capeHistory, games: f"{max(capeHistory)} J/kg" if capeHistory else None], 
                                    ["Loswest cape", lambda timeHistory, capeHistory, games: f"{min(capeHistory)} J/kg" if capeHistory else None], 
                                    ["Average cape", lambda timeHistory, capeHistory, games: f"{round(sum(capeHistory)/len(capeHistory))} J/kg" if capeHistory else None], 
                                    ["Avg reroll time", lambda timeHistory, capeHistory, games: f"{round(sum(timeHistory)/len(timeHistory), 1)} sec" if timeHistory else None],
                                    ["Rerolls SGS", lambda timeHistory, capeHistory, games: min([game.rerollsSGS for game in games]) if games else None],
                                    ["Servers rolled", lambda timeHistory, capeHistory, games: len(capeHistory) if capeHistory else None]
                                    ]:
            label = tk.Label(self.left_side_SF)
            label.pack(anchor=tk.W)

            self.recordsUpdateCallbacks.append([recordType, command, label])
   
        right_sf_canvas = tk.Canvas(self.right_side, width=500)
        self.right_side_SF = tk.Frame(right_sf_canvas)

        scrollbar = tk.Scrollbar(self.right_side, orient=tk.VERTICAL, command=right_sf_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        right_sf_canvas.configure(yscrollcommand=scrollbar.set)

        right_sf_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_sf_canvas.create_window((0,0), window=self.right_side_SF, anchor=tk.NW)

        self.right_side_SF.bind("<Configure>", \
            lambda event, canvas=right_sf_canvas: canvas.configure(scrollregion=canvas.bbox("all")))

class CONFIG:
    TEMPLATE = {
        "webhook": {
            "url": [str, ""],
            "ping id": [str, ""]
        },
        "cape": {
            "highest": [int, 7000],
            "lowest": [int, 300]
        },
        "paths": {
            "microsoft roblox": [str, ""],
            "roblox player": [str, ""],
        }
    }

    CONFIG_FILE = ".config.json"

    def __init__(self, parent):
        self.root = tk.Toplevel(parent)
        self.root.withdraw()

        self.updateList = []

        self.load()
        self.write()

        self.setup()

    def setup(self):
        self.root.title("Re:Twisted - config")
        self.root.geometry("400x900")
        self.root.resizable(True, True)

        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close(False))

        bottomFrame = tk.Frame(self.root)
        bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Button(bottomFrame, text="Save", command=lambda: self.close(True)) \
            .pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)
        
        tk.Button(bottomFrame, text="Close", command=lambda: self.close(False)) \
            .pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5, pady=5)

        self.configGUIGenerator(self.TEMPLATE, self.root)

    def load(self):
        try:
            raw = json.load(open(self.CONFIG_FILE, "r"))
        except:
            raw = {}
        self.config = self.fitDictToDict(self.TEMPLATE, raw)
        self.newConfig = self.config

    def write(self):
        with open(self.CONFIG_FILE, "w") as file:
            json.dump(self.config, file)
            file.close()        

    def open(self):
        self.load()

        for up in self.updateList:
            up()

        self.root.deiconify()

    def close(self, save):
        if save:
            self.config = self.fitDictToDict(self.TEMPLATE, self.newConfig)

            self.write()

        self.root.withdraw()

    def getSetting(self, path):
        return self.getInDict(self.config, path)

    def configGUIGenerator(self, template, master, path=[]):
        if path:
            last = path[-1].capitalize()

            frame = tk.Frame(master)
            frame.pack(anchor=tk.W, padx=(max(0, (len(path) - 1) * 25), 0))

            tk.Label(frame, text=last) \
                .pack(anchor=tk.W)
        else:
            frame = master

        match template:
            case dict():
                for key, item in template.items():
                    self.configGUIGenerator(item, frame, path=path + [key])
            case list():
                inpt = tk.StringVar(value=self.getInDict(self.newConfig, path))
                self.updateList.append(lambda: inpt.set(self.getInDict(self.newConfig, path)))

                match template[0]():
                    case int():
                        def validate():
                            out = int("0" + "".join([n for n in inpt.get() if n.isnumeric()]))
                            inpt.set(out)

                            self.setInDict(self.newConfig, path, out)
                            return True
                    case str():
                        def validate():
                            out = inpt.get()
                            inpt.set(out)

                            self.setInDict(self.newConfig, path, out)
                            return True

                inpt.trace_add("write", lambda *e: validate())

                tk.Entry(frame, textvariable=inpt) \
                    .pack(pady=(0, 15), side=tk.LEFT)

    @staticmethod
    def getInDict(config, path):
        tmp = config
        for arg in path:
            if arg in tmp:
                tmp = tmp[arg]
                continue
            return None
        return tmp
    
    @staticmethod
    def setInDict(config, path, value):
        tmp = config
        for arg in path[:-1]:
            if arg in tmp:
                tmp = tmp[arg]
                continue
            return
        tmp[path[-1]] = value
    
    @staticmethod
    def defaultIfInvalid(value, type, default):
        return value if isinstance(value, type) else default

    @staticmethod
    def fitDictToDict(template, config, path=[]):
        match template:
            case dict():
                return { key: CONFIG.fitDictToDict(item, config, path=path + [key]) \
                        for key, item in template.items() }
            case list():
                conf = CONFIG.getInDict(config, path)
                return CONFIG.defaultIfInvalid(conf, template[0], template[1])
        
                            
if __name__ == '__main__':
    GUI()
