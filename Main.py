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

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

VERSION = "1.0"

W, H = 975, 850
FOLDER = "assets/"

FRIEND = cv2.imread(resource_path(FOLDER + "friend.png"))
JOIN_FRIEND = cv2.imread(resource_path(FOLDER + "join-friend.png"))

JOIN_BTN = cv2.imread(resource_path(FOLDER + "join-button.png"))

PLAY = cv2.imread(resource_path(FOLDER + "play.png"))
MENU = cv2.imread(resource_path(FOLDER + "menu-icon.png"))
WEATHER = cv2.imread(resource_path(FOLDER + "weather-icon.png"))

STATS = cv2.imread(resource_path(FOLDER + "stats.png"))
STATS_MASK = cv2.cvtColor(cv2.imread(resource_path(FOLDER + "stats-mask.png")), cv2.COLOR_BGR2GRAY)
STATS_DATA_MASK = cv2.cvtColor(cv2.imread(resource_path(FOLDER + "stats-data-mask.png")), cv2.COLOR_BGR2GRAY)

TWISTED = cv2.imread(resource_path(FOLDER + "twisted.png"))

DESKTOP = win32gui.GetDesktopWindow()

    
class IHANDLER(threading.Thread):
    def __init__(self, pausedE):
        super().__init__()
        self.daemon = True
        self.name = "Input Handler"

        self.eventsQueue = []
        self.event = threading.Event()

        self.pausedE = pausedE
        self.statusCallback = None

        self.start()

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
        func = lambda: self.click(win, x, y)
        self.eventsQueue.append(func)
        self.event.set()

        return func

    @staticmethod
    def pressKey(win, key, time=.25):
        IHANDLER.focuswindow(win)

        pydirectinput.keyDown(key)

        sleep(time)

        pydirectinput.keyUp(key)

    def qPressKey(self, win, key):
        func = lambda: self.pressKey(win, key)
        self.eventsQueue.append(func)
        self.event.set()

        return func
    
    def awaitFunc(self, func):
        while func in self.eventsQueue:
            sleep(.1)


    def run(self):
        while True:
            self.event.wait()
            self.pausedE.wait()

            if self.eventsQueue:
                self.eventsQueue[0]()
                del self.eventsQueue[0]
            else:
                self.event.clear()

class GAME(threading.Thread):
    CLASSNAMES = {
        "WINDOWSCLIENT": "Roblox Player",
        "ApplicationFrameWindow": "Microsoft Roblox"
    }

    def __init__(self, win, IHandler, getCfg, dataCallback, pausedE, server=0):
        super().__init__()
        self.daemon = True

        self.win = win
        self.name = win32gui.GetClassName(self.win)
        self.IHandler = IHandler
        self.lPaused = threading.Event()
        self.getCfg = getCfg
        self.pausedE = pausedE

        self.dataCallback = dataCallback
        self.historyTextCallback = None

        self.history = []

        self.setServer(server)

        self.start()

    def crashDetection(self):
        match self.name:
            case "WINDOWSCLIENT":
                if (win := win32gui.FindWindow(None, "Roblox Crash")) == 0:
                    return False
                win32gui.PostMessage(win, win32con.WM_CLOSE, 0, 0)

                for root, dirs, files in os.walk(os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs")):
                    if (file := 'Roblox Player.lnk') in files:
                        path = os.path.join(root, file)
                        break

            case "ApplicationFrameWindow":
                if win32gui.IsWindow(self.win):
                    return False
                
                robloxFamilyName = os.popen('powershell Get-AppxPackage -Name "ROBLOXCORPORATION.ROBLOX" | findstr /c:"PackageFamilyName"').read().split(":")[1].strip()
                path = f"shell:appsFolder\{robloxFamilyName}!App"
                
            case _:
                return None
                            
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
        self.server = max(0, server - 1)
        if server <= 0:
            self.lPaused.clear()
        else:
            self.lPaused.set()

    def resize(self):
        state = win32gui.GetWindowPlacement(self.win)[1]
        if state in [2, 3]:
            win32gui.ShowWindow(self.win, 1)

        left, top, right, bot = win32gui.GetWindowRect(self.win)
        w, h = right - left, bot - top
        if w != W or h != H:
            win32gui.MoveWindow(self.win, left, top, W, H, True)

    def getscr(self):
        self.pausedE.wait()
        self.lPaused.wait()

        self.crashDetection()

        self.resize()

        left, top, right, bot = win32gui.GetWindowRect(self.win)
        w, h = right - left, bot - top

        while True:
            try:
                hwndDC = win32gui.GetWindowDC(DESKTOP)
                mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
                saveDC = mfcDC.CreateCompatibleDC()

                saveBitMap = win32ui.CreateBitmap()
                saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

                saveDC.SelectObject(saveBitMap)

                windll.user32.PrintWindow(self.win, saveDC.GetSafeHdc(), 2)

                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)

                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(DESKTOP, hwndDC)
            except:
                continue
            break

        img = np.frombuffer(bmpstr, dtype=np.uint8)
        img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
        img = img[:,:,:3]

        return img.astype(dtype=np.uint8)
    
    def findCoords(self, image, interval=.25, threshold=.1):
        ox, oy = None, None
        while True:
            error, (x, y) = self.findPos(image, self.getscr())
            
            if error <= threshold:
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

            self.IHandler.qClick(self.win, x, y)
    
    def openServers(self):
        self.findAndClick([FRIEND, JOIN_FRIEND])

        while not self.findPos(JOIN_BTN, self.getscr())[0] <= .005:
            sleep(.25)

    def joinServer(self, n):
        servers = self.findMultiplePos(JOIN_BTN, self.getscr())
        pos = servers[max(min(len(servers) - 1, n), 0)]

        self.IHandler.qClick(self.win, pos[0], pos[1])

    def quitGame(self):
        self.IHandler.qPressKey(self.win, "esc")

        self.IHandler.qPressKey(self.win, "l")

        self.IHandler.qPressKey(self.win, "enter")

    def restartGame(self):
        self.quitGame()
        self.openServers()
        self.joinServer(self.server)

    def getInfo(self):
        ox, oy = None, None
        while True:
            sleep(.25)
            scr = self.getscr()

            res = cv2.matchTemplate(scr, STATS, cv2.TM_SQDIFF_NORMED, mask=STATS_MASK)
            lerror, herror, loc, _ = cv2.minMaxLoc(res)
            success = lerror <= .1
            x, y = loc
            
            if not success:
                ox, oy = None, None
                continue
            else:
                if ox != x or oy != y:
                    ox, oy = x, y
                    continue

            h, w = STATS.shape[:2]
            ih, iw = scr.shape[:2]

            clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

            table = scr[clamp(y, 0, ih - h):clamp(y + h, h, ih), 
                        clamp(x, 0, iw - w):clamp(x + w, w, iw)]

            stats = []

            contours, _ = cv2.findContours(STATS_DATA_MASK, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours[::-1]:
                contourMask = np.zeros_like(STATS_DATA_MASK)

                cv2.drawContours(contourMask, [contour], 0, (255), -1)

                cropped = cv2.bitwise_or(table, table, mask=contourMask)

                cropped = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

                x, y, w, h = cv2.boundingRect(cv2.findNonZero(cropped))
                cropped = cropped[y:y+h, x:x+w]

                cropped = cv2.threshold(cropped, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

                cropped = cv2.resize(cropped, (np.array(cropped.shape) * 3)[::-1], interpolation = cv2.INTER_LINEAR)

                
                value = pytesseract.image_to_string(cropped, config='digits').strip()

                try:
                    value = int(value)
                except ValueError:
                    value = float(value)

                stats.append(value)
            
            ELEMENTS = ["TEMPERATURE", "DEW POINT", "LAPSE RATES", "HUMIDITY", "CAPE"]

            if len(stats) != 2 * len(ELEMENTS):
                continue

            return {
                "CURRENT": {name: value for name, value in zip(ELEMENTS, stats[::2])},
                "FORECAST": {name: value for name, value in zip(ELEMENTS, stats[1::2])}
            }

    def run(self):
        timebeg = time.time()
        self.openServers()
        self.joinServer(self.server)
        while True:
            self.findAndClick([PLAY, MENU, WEATHER])

            stats = self.getInfo()
            cape = stats["FORECAST"]["CAPE"]

            timeend = time.time()
            self.history.append([timeend - timebeg, cape])
            self.historyTextCallback(timeend, cape)

            self.dataCallback(stats)

            timebeg = time.time()
            self.restartGame()

    @staticmethod
    def findPos(template, image):
        res = cv2.matchTemplate(image, template, cv2.TM_SQDIFF_NORMED)
        error, _, loc, _ = cv2.minMaxLoc(res)
        x, y = loc

        h, w = template.shape[:2]
        return error, (x + w//2, y + h//2)
    
    @staticmethod
    def findMultiplePos(template, image, threshold=.9):
        res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)

        h, w = template.shape[:2]
        return [(pos[0] + w//2, pos[1] + h//2) for pos in zip(*loc[::-1])]

class DiscordWebHook:
    def send(config, stats):
        if not (url := config(["webhook", "url"])):
            return
        
        post(url, json={
            "username": "Re:Twisted bot",
            # "avatar_url": "",
            "content" : f"<@{config(['webhook', 'ping id'])}>" if config(['webhook', 'ping id']) else "",
            "embeds": [{
                "title": "Winds are picking up on speed :cloud_tornado:",
                "color": "333",

                "fields": [{
                    "name": f"**{foc}**",
                    "value": "```" + "\n".join([f"{key}: {value}" for key, value in item.items()]) + "```",
                    "inline": True,
                } for foc, item in stats.items()],
            }]
        })

class GUI:
    class PausePopUP:
        def __init__(self, parent, pausedE):
            self.root = tk.Toplevel(parent)
            self.root.withdraw()

            self.pausedE = pausedE

            self.setup()

        def setup(self):
            self.root.title("Re:Twisted - pop up")
            self.root.geometry("350x150")
            self.root.resizable(False, False)

            self.root.protocol("WM_DELETE_WINDOW", self.close)
            
            frame = tk.Frame(self.root)
            frame.pack(padx=15, pady=15, fill=tk.BOTH, expand=True)

            tk.Label(frame, text="Good server have been found", font=(None, 16)).pack()
            tk.Label(frame, text="Would you like to continue rerolling?", font=(None, 14)).pack()

            buttons = tk.Frame(frame)
            buttons.pack(side=tk.BOTTOM, fill=tk.X, expand=True)

            tk.Button(buttons, text="Yes", font=(None, 14), command=self.continueAndClose) \
                .pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            tk.Button(buttons, text="No", font=(None, 14), command=self.close) \
                .pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)
            
        def continueAndClose(self):
            self.pausedE.unpause()
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

            inte = tk.StringVar(value=(self.game.server + 1))
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
            
            tk.Label(info_frame_bottom, state=tk.DISABLED, text="Which server (from top) will be selected", font=(None, 10), anchor=tk.W) \
                .pack(fill=tk.X, side=tk.TOP)
            tk.Label(info_frame_bottom, state=tk.DISABLED, text="0 means, pause rolling for this client", font=(None, 10), anchor=tk.W) \
                .pack(fill=tk.X, side=tk.TOP)

        def appendToHistory(self, timestamp, num):
            self.historyText.configure(state=tk.NORMAL)
            self.historyText.insert("1.0", f"{time.strftime('%H:%M:%S', time.localtime(timestamp))} - {num} J/kg\n")
            self.historyText.configure(state=tk.DISABLED)

        def destroy(self):
            self.frame.pack_forget()

    def __init__(self):
        self.root = tk.Tk()

        self.pausedE = threading.Event()
        self.pausedE.pause = self.pause
        self.pausedE.unpause = self.unpause

        self.config = CONFIG(self.root)
        self.popup = self.PausePopUP(self.root, self.pausedE)
        self.ihandler = IHANDLER(self.pausedE)

        self.setup()

        self.games = []
        for className in GAME.CLASSNAMES.keys():
            if (win := win32gui.FindWindow(className, "Roblox")) != 0:
                self.newGame(win)

        self.updateHisotry()

        self.root.mainloop()

    def newGame(self, win):
        game = GAME(win, self.ihandler, self.config.getSetting, self.handleData, self.pausedE, server=(len(self.games) + 1))

        self.games.append(game)
        self.GameFrame(self.right_side_SF, game)

    def handleData(self, stats):
        cape = stats["FORECAST"]["CAPE"]

        if cape >= self.config.getSetting(["cape", "highest"]) or \
           cape <= self.config.getSetting(["cape", "lowest"]):
            self.popup.open()
            self.pause()

            DiscordWebHook.send(self.config.getSetting, stats)

        self.updateHisotry()
    
    def updateHisotry(self):
        history = [stat for game in self.games for stat in game.history]
        timeHistory = [time for time, cape in history]
        capeHistory = [cape for time, cape in history]

        for recordType, command, label in self.recordsUpdateCallbacks:
            label.config(text=f"{recordType}: {command(timeHistory, capeHistory)}")

    def pause(self):
        self.status.config(text="Status - Paused")
        self.pausedE.clear()

    def unpause(self):
        self.status.config(text="Status - Running")
        self.pausedE.set()

    def setup(self):
        self.root.title("Re:Twisted")
        self.root.geometry("850x500")
        self.root.resizable(False, True)
        self.root.iconphoto(True, tk.PhotoImage(file=resource_path("icon.png")))

        self.root.defaultFont = font.nametofont("TkDefaultFont")
        self.root.defaultFont.configure(family="Comic Sans MS", size=18)

        self.lbg = "#ccc"
        self.left_side = tk.Frame(self.root, width=350, background=self.lbg)
        self.left_side.pack(side=tk.LEFT, fill=tk.BOTH)
        self.left_side.pack_propagate(False)

        self.right_side = tk.Frame(self.root, width=500)
        self.right_side.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.right_side.pack_propagate(False)


        tk.Label(self.left_side, text="Re:Twisted", font=(None, 20), background=self.lbg) \
            .pack(side=tk.TOP)
        
        tk.Label(self.left_side, text=f"version {VERSION}", font=(None, 12), background=self.lbg) \
            .pack(side=tk.TOP, pady=(0, 15))
        
        self.status = tk.Label(self.left_side, text="Status - Paused", background=self.lbg)
        self.status.pack(side=tk.TOP)

        server_buttons = tk.Frame(self.left_side, background=self.lbg)
        server_buttons.pack( fill=tk.X, side=tk.TOP)
        tk.Button(server_buttons, text="Start", command=self.unpause) \
            .pack(fill=tk.X, side=tk.LEFT, anchor=tk.N, pady=5, padx=5, expand=True)
        tk.Button(server_buttons, text="Pause", command=self.pause) \
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
        for recordType, command in [["Highest cape", lambda timeHistory, capeHistory: f"{max(capeHistory)} J/kg" if capeHistory else None], 
                                    ["Lowest cape", lambda timeHistory, capeHistory: f"{min(capeHistory)} J/kg" if capeHistory else None], 
                                    ["Average cape", lambda timeHistory, capeHistory: f"{round(sum(capeHistory)/len(capeHistory))} J/kg" if capeHistory else None], 
                                    ["Avg reroll time", lambda timeHistory, capeHistory: f"{round(sum(timeHistory)/len(timeHistory), 1)} sec" if timeHistory else None],
                                    ["Servers rolled", lambda timeHistory, capeHistory: len(capeHistory) if capeHistory else None]
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
            "url": [str, "", \
                    "Webhook url where bot will send message on succesful find"],
            "ping id": [str, "", \
                        "User / Role which will be pinged in message"]
        },
        "cape": {
            "highest": [int, 7000, \
                        "Will stop rolling, if it's over this number"],
            "lowest": [int, 300, \
                        "Will stop rolling, if it's under this number"]
        },
        "paths": {
            "tesseract": [str, "C:\\Program Files\\Tesseract-OCR\\tesseract.exe", \
                        "Path to tesseract executable for OCR to work"]
        }
    }

    CONFIG_FILE = ".config.json"

    def __init__(self, parent):
        self.root = tk.Toplevel(parent)
        self.root.withdraw()

        self.updateList = []

        self.load()
        self.write()

        self.tesseract = Tesseract(self.setSetting, self.getSetting, parent)

        self.setup()

    def setup(self):
        self.root.title("Re:Twisted - config")
        self.root.geometry("400x600")
        self.root.resizable(True, True)

        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close(False))

        bottomFrame = tk.Frame(self.root)
        bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Button(bottomFrame, text="Save", command=lambda: self.close(True)) \
            .pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)
        
        tk.Button(bottomFrame, text="Close", command=lambda: self.close(False)) \
            .pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5, pady=5)
        
        canvas = tk.Canvas(self.root, width=500)
        frame = tk.Frame(canvas)

        vscrollbar = tk.Scrollbar(self.root, orient=tk.VERTICAL, command=canvas.yview)
        vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=vscrollbar.set)

        hscrollbar = tk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=canvas.xview)
        hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.configure(xscrollcommand=hscrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0,0), window=frame, anchor=tk.NW)

        frame.bind("<Configure>", \
            lambda event, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")))

        self.configGUIGenerator(self.TEMPLATE, frame)

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

            self.tesseract.loadTesseract()

            self.write()

        self.root.withdraw()

    def getSetting(self, path):
        return self.getInDict(self.config, [e.lower() for e in path])

    def setSetting(self, path, value):
        self.setInDict(self.config, path, value)
        self.write()

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

                inpt.trace_add("write", lambda *e: self.validateAndSet(path, inpt))

                tk.Label(frame, state=tk.DISABLED, text=template[2], font=(None, 10), anchor=tk.W) \
                    .pack(fill=tk.X, side=tk.TOP)

                tk.Entry(frame, textvariable=inpt, width=50) \
                    .pack(pady=(0, 15), side=tk.LEFT)
                
    def validateAndSet(self, config, inpt):
        dataType = self.getInDict(self.TEMPLATE, config)[0]
        match dataType():
            case int():
                out = "0" + "".join([n for n in inpt.get() if n.isnumeric()])

            case _:
                out = inpt.get()
        out = dataType(out)

        inpt.set(out)

        self.setInDict(self.newConfig, config, out)
        return True

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
            
class Tesseract:
    def __init__(self, setSetting, getSetting, parent):
        self.setSetting = setSetting
        self.getSetting = getSetting

        self.root = tk.Toplevel(parent)
        self.root.withdraw()

        self.setup()

        self.loadTesseract()

    def setup(self):
        self.root.title("Re:Twisted - tesseract setup")
        self.root.geometry("450x275")
        self.root.resizable(False, False)

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        
        frame = tk.Frame(self.root)
        frame.pack(padx=15, pady=15, fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Tesseract not detected", font=(None, 16)).pack()
        tk.Label(frame, text="Set the path manually or use auto search within the folder.", font=(None, 12)).pack()

        # BUTTONS FRAME
        buttons = tk.Frame(frame)
        buttons.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        tk.Button(buttons, text="Save", font=(None, 14), command=lambda: self.close(True)) \
            .pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(buttons, text="Close", font=(None, 14), command=self.close) \
            .pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
        
        # PATH FRAME
        pathFrame = tk.Frame(frame)
        pathFrame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        tk.Label(pathFrame, text="Path", font=(None, 12)).pack(side=tk.LEFT, pady=5)

        self.pathVar = tk.StringVar(value=self.getSetting(["paths", "tesseract"]))

        pathE = tk.Entry(pathFrame, textvariable=self.pathVar)
        pathE.pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.N, pady=5, padx=5, expand=True)
        
        # AUTOSEARCH FRAME
        autosearchFrame = tk.Frame(frame)
        autosearchFrame.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(autosearchFrame, text="Auto-find", font=(None, 12)).pack(side=tk.TOP, fill=tk.X)

        autosearchVar = tk.StringVar(value="C:\\Program Files")
        def autosearchFun():
            for root, dirs, files in os.walk(autosearchVar.get()):
                if (file := "tesseract.exe") in files:
                    self.pathVar.set(os.path.join(root, file))
                    return


        tk.Entry(autosearchFrame, textvariable=autosearchVar) \
            .pack(fill=tk.BOTH, side=tk.LEFT, anchor=tk.N, pady=5, padx=5, expand=True)
        
        tk.Button(autosearchFrame, text="Find", font=(None, 14), command=autosearchFun) \
            .pack(fill=tk.X, side=tk.RIGHT, anchor=tk.N, pady=5, padx=5, expand=True)
        

    def loadTesseract(self):
        pytesseract.pytesseract.tesseract_cmd = self.getSetting(["paths", "tesseract"])

        try:
            pytesseract.get_tesseract_version()
        except:
            self.open()

    def open(self):
        self.pathVar.set(self.getSetting(["paths", "tesseract"]))
        self.root.deiconify()

    def close(self, save=False):
        path = self.pathVar.get()
        if save and path:
            self.setSetting(["paths", "tesseract"], path)

        self.root.withdraw()
                            
if __name__ == '__main__':
    GUI()
