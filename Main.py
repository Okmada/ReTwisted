from tkinter import font
from ctypes import windll
from time import sleep
from requests import post
import win32clipboard
import win32gui
import win32ui
import win32con
import numpy as np
import cv2
import threading
import platform
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


VERSION = "1.3"

W, H = 975, 850
FOLDER = "assets/"

DESKTOP = win32gui.GetDesktopWindow()

class Images:
    _Images = {
        "twisted": {
            "light": cv2.imread(resource_path(FOLDER + "twisted.png")),
            "dark": cv2.imread(resource_path(FOLDER + "twisted-dark.png"))
        },
        "friend": {
            "light": cv2.imread(resource_path(FOLDER + "friend.png")),
            "dark": cv2.imread(resource_path(FOLDER + "friend-dark.png"))
        },
        "join friend": {
            "light": cv2.imread(resource_path(FOLDER + "join-friend.png")),
            "dark": cv2.imread(resource_path(FOLDER + "join-friend-dark.png"))
        },
        "join btn": {
            "light": cv2.imread(resource_path(FOLDER + "join-button.png")),
            "dark": cv2.imread(resource_path(FOLDER + "join-button-dark.png"))
        },
        "play": cv2.imread(resource_path(FOLDER + "play.png")),
        "menu": cv2.imread(resource_path(FOLDER + "menu-icon.png")),
        "weather": cv2.imread(resource_path(FOLDER + "weather-icon.png")),
        "stats": cv2.imread(resource_path(FOLDER + "stats.png")),
        "stats mask": cv2.cvtColor(cv2.imread(resource_path(FOLDER + "stats-mask.png")), cv2.COLOR_BGR2GRAY),
        "stats data mask": cv2.cvtColor(cv2.imread(resource_path(FOLDER + "stats-data-mask.png")), cv2.COLOR_BGR2GRAY)
    }

    @staticmethod
    def get(imageName, theme = None):
        imageName = imageName.lower()
        if imageName not in Images._Images.keys():
            return None
        
        image = Images._Images[imageName]

        if not isinstance(image, dict):
            return image
        else:
            theme = theme.lower()

            if theme and theme in image.keys():
                return image[theme]
            return None


class InputHandler(threading.Thread):
    def __init__(self, pausedE):
        super().__init__()
        self.daemon = True
        self.name = "Input Handler"

        self.counter = 0
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
        InputHandler.focuswindow(win)

        mx, my = win32gui.GetWindowRect(win)[:2]
        fx, fy = mx + x, my + y

        match win32gui.GetClassName(win):
            case "WINDOWSCLIENT":
                InputHandler.focuswindow(DESKTOP)
                pydirectinput.doubleClick(fx, fy)
            case "ApplicationFrameWindow":
                pydirectinput.leftClick(fx, fy)

    def qClick(self, win, x, y):
        func = lambda: self.click(win, x, y)
        self.eventsQueue.append(func)
        self.event.set()

        return func

    @staticmethod
    def pressKey(win, key, time=.25):
        InputHandler.focuswindow(win)

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
                try:
                    self.eventsQueue[0]()
                except:
                    pass
                finally:
                    del self.eventsQueue[0]

                    self.counter += 1
            else:
                self.event.clear()


class Game(threading.Thread):
    CLASSNAMES = {
        "WINDOWSCLIENT": "Roblox Player",
        "ApplicationFrameWindow": "Microsoft Roblox"
    }

    MULTIPLIERS = {
        "WINDOWSCLIENT": 1.5,
        "ApplicationFrameWindow": 3
    }

    def __init__(self, win, parent, IHandler, getCfg, dataCallback, pausedE, server=0):
        super().__init__()
        self.daemon = True

        self.win = win
        self.name = win32gui.GetClassName(self.win)
        self.IHandler = IHandler
        self.lPaused = threading.Event()
        self.getCfg = getCfg
        self.pausedE = pausedE
        self.sfpopup = Gui.ScaleFactorPopup(parent, self.getName())

        self.dataCallback = dataCallback
        self.historyTextCallback = None

        self.history = []

        self.status = None
        self.timeout = None

        self.setServer(server)
    
        self.frame = tk.Frame(parent, width=470, height=250, background="#aaa")
        self.frame.pack(padx=5, pady=5)
        self.frame.pack_propagate(False)

        self.setup()

        self.start()

    def setup(self):
        history_frame = tk.Frame(self.frame, width=210)
        history_frame.pack_propagate(False)
        history_frame.pack(padx=5, pady=5, side=tk.RIGHT, fill=tk.Y)

        self.historyText = tk.Text(history_frame, state=tk.DISABLED)
        scrollbar = tk.Scrollbar(history_frame, command=self.historyText.yview)
        self.historyText['yscrollcommand'] = scrollbar.set

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.historyText.pack(expand=True, fill=tk.X)

        info_frame = tk.Frame(self.frame, width=500)
        info_frame.pack_propagate(False)
        info_frame.pack(padx=5, pady=5, side=tk.LEFT, fill=tk.Y)

        tk.Label(info_frame, text=self.getName()).pack(side=tk.TOP, pady=(10, 0))

        info_frame_bottom = tk.Frame(info_frame)
        info_frame_bottom.pack(padx=5, pady=5, fill=tk.X, side=tk.BOTTOM)

        self.theme = tk.StringVar()
        self.theme.set("Dark" if self.isDarkmode() else "Light")

        theme_frame = tk.Frame(info_frame_bottom)
        theme_frame.pack(fill=tk.X, side=tk.TOP, pady=1)
        tk.Label(theme_frame, text="Theme:") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N, padx=(0, 5))
        tk.OptionMenu(theme_frame, self.theme, "Light", "Dark") \
            .pack(fill=tk.X, side=tk.RIGHT, anchor=tk.N, expand=True)
    
        server = tk.StringVar(value=(self.server + 1))

        def validateServer():
            num = max(0, int("0" + "".join([n for n in server.get() if n.isnumeric()])))
            server.set(num)
            self.setServer(num)
            return True

        server.trace_add("write", lambda *e: validateServer())

        # tk.Label(info_frame_bottom, text="Server settings") \
        #     .pack(fill=tk.X, side=tk.TOP, anchor=tk.N, pady=5, padx=5, expand=True)

        server_frame = tk.Frame(info_frame_bottom)
        server_frame.pack(fill=tk.X, side=tk.TOP, pady=1)
        tk.Label(server_frame, text="Server:") \
            .pack(fill=tk.Y, side=tk.LEFT, anchor=tk.N, padx=(0, 5))
        tk.Entry(server_frame, textvariable=server) \
            .pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.N, expand=True)

        tk.Label(info_frame_bottom, state=tk.DISABLED, text="Which server (from top) will be selected\n0 means, pause rolling for this client", 
                 font=(None, 10), anchor=tk.W, justify=tk.LEFT).pack(fill=tk.X, side=tk.TOP)

        copyScreenshotBtn = tk.Button(info_frame_bottom, text="Copy screenshot",
                                      command=lambda: Gui.coppiedButton(copyScreenshotBtn, "Copy screenshot", self.copyScreenshot))
        copyScreenshotBtn.pack(fill=tk.X, side=tk.TOP, pady=5, padx=5)

    def copyScreenshot(self):
        image = self.getscr(True)

        data = cv2.imencode('.dib', image)[1]

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data[14:])
        win32clipboard.CloseClipboard()

    def crashDetection(self):
        match self.name:
            case "WINDOWSCLIENT":
                if (win := win32gui.FindWindow(None, "Roblox Crash")) != 0:
                    win32gui.PostMessage(win, win32con.WM_CLOSE, 0, 0)
                elif not win32gui.IsWindow(self.win):
                    pass
                else:
                    return False

                for root, dirs, files in os.walk(
                        os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs")):
                    if (file := 'Roblox Player.lnk') in files:
                        path = os.path.join(root, file)
                        break

            case "ApplicationFrameWindow":
                if win32gui.IsWindow(self.win):
                    return False

                robloxFamilyName = os.popen('powershell Get-AppxPackage -Name "ROBLOXCORPORATION.ROBLOX" | findstr /c:"PackageFamilyName"').read().split(":")[1].strip()
                path = f"shell:appsFolder\\{robloxFamilyName}!App"

            case _:
                return None

        os.startfile(path)

        while (newWin := win32gui.FindWindow(self.name, "Roblox")) in [self.win, 0]:
            sleep(.1)
        self.win = newWin

        self.awaitFind("twisted", threshold=0.005)
        raise Exception()

    def timeOutDetection(self):
        maxTimeout = self.getCfg(["timeout"])

        if maxTimeout <= 0:
            return

        if not self.timeout:
            self.timeout = time.time()

        elif self.timeout + maxTimeout <= time.time():
            self.timeout = None
            self.closeRoblox()

    def closeRoblox(self):
        win32gui.PostMessage(self.win, win32con.WM_CLOSE, 0, 0)

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

    def getscr(self, force=False):
        if not force:
            if not self.lPaused.is_set() or not self.pausedE.is_set():
                self.timeout = None

                self.pausedE.wait()
                self.lPaused.wait()

            self.timeOutDetection()

        self.crashDetection()

        self.resize()

        while (scaleFactor := windll.user32.GetDpiForWindow(self.win) / 96.0) != 1:
            if not self.sfpopup.root.winfo_viewable():
                self.sfpopup.root.deiconify()
            sleep(.1)
        self.sfpopup.root.withdraw()

        left, top, right, bot = win32gui.GetWindowRect(self.win)
        w, h = round((right - left) * scaleFactor), round((bot - top) * scaleFactor)

        while True:
            try:
                hwndDC = win32gui.GetWindowDC(DESKTOP)
                mfcDC = win32ui.CreateDCFromHandle(hwndDC)
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
        img = img[:, :, :3]

        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_LANCZOS4)

        return img.astype(dtype=np.uint8)

    def awaitFind(self, images, threshold=.1, click=True, interval=.25):
        if not isinstance(images, list):
            images = [images]

        for image in images:
            ox, oy = None, None
            while True:
                error, (x, y) = self.findPos(Images.get(image, self.theme.get()), self.getscr())

                self.status = f"img {image}, err {error}, coords {(x, y)}"

                if error <= threshold:
                    if ox == x and oy == y:
                        break
                    ox, oy = x, y
                else:
                    ox, oy = None, None

                sleep(interval)

            if click:
                self.IHandler.qClick(self.win, x, y)

    def isDarkmode(self):
        whitePixels = cv2.inRange(self.getscr(True), (128, 128, 128), (255, 255, 255))
        blackPixels = cv2.bitwise_not(whitePixels)

        wpCount = cv2.countNonZero(whitePixels)
        bpCount = cv2.countNonZero(blackPixels)

        ratio = wpCount/bpCount
        return ratio <= .25

    def openServers(self):
        self.awaitFind(["friend", "join friend"], threshold=.075)

        self.awaitFind("join btn", threshold=.025, click=False)

    def joinServer(self):
        for _ in range(max(0, int((self.server - 1) * self.MULTIPLIERS[self.name]))):
            self.IHandler.qClick(self.win, W - 20, H - 20)
        self.IHandler.awaitFunc(self.IHandler.qClick(self.win, W - 20, H - 20))

        sleep(.5)

        match self.theme.get().lower():
            case "light":
                threshold = 0.005
            case "dark":
                threshold = 0.025

        servers = self.findPos(Images.get("join btn", self.theme.get()), self.getscr(), threshold)
        (x, y) = servers[min(1, self.server)]

        self.IHandler.qClick(self.win, x, y)

    def quitGame(self):
        self.IHandler.qPressKey(self.win, "esc")

        self.IHandler.qPressKey(self.win, "l")

        self.IHandler.qPressKey(self.win, "enter")

    def getInfo(self):
        ox, oy = None, None
        while True:
            sleep(.25)

            if self.name == "ApplicationFrameWindow":
                self.IHandler.awaitFunc(self.IHandler.qClick(self.win, W // 2, H // 4 * 3))

            scr = self.getscr()

            res = cv2.matchTemplate(scr, Images.get("stats"), cv2.TM_SQDIFF_NORMED, mask=Images.get("stats mask"))
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

            h, w = Images.get("stats").shape[:2]
            ih, iw = scr.shape[:2]

            clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

            table = scr[clamp(y, 0, ih - h):clamp(y + h, h, ih),
                    clamp(x, 0, iw - w):clamp(x + w, w, iw)]

            stats = []

            contours, _ = cv2.findContours(Images.get("stats data mask"), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours[::-1]:
                contourMask = np.zeros_like(Images.get("stats data mask"))

                cv2.drawContours(contourMask, [contour], 0, (255), -1)

                cropped = cv2.bitwise_or(table, table, mask=contourMask)

                cropped = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

                x, y, w, h = cv2.boundingRect(cv2.findNonZero(cropped))
                cropped = cropped[y:y + h, x:x + w]

                cropped = cv2.threshold(cropped, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

                cropped = cv2.resize(cropped, (np.array(cropped.shape) * 4)[::-1], interpolation=cv2.INTER_NEAREST)  

                cropped = cv2.blur(cropped, (5, 5))

                value = pytesseract.image_to_string(cropped, config='digits').strip()

                try:
                    value = int(value)
                except ValueError:
                    value = float(value[::-1].replace(".", "", max(0, value.count(".") - 1))[::-1])

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
        while True:
            try:
                self.openServers()
                self.joinServer()

                self.awaitFind(["play", "menu", "weather"])

                stats = self.getInfo()
                cape = stats["FORECAST"]["CAPE"]

                timeend = time.time()
                self.history.append([timeend - timebeg, cape])

                self.historyText.configure(state=tk.NORMAL)
                self.historyText.insert("1.0", f"{time.strftime('%H:%M:%S', time.localtime(timeend))} - {cape} J/kg\n")
                self.historyText.configure(state=tk.DISABLED)

                self.dataCallback(stats)

                timebeg = time.time()

                self.quitGame()
            except:
                timebeg = time.time()
            finally:
                self.timeout = None

    @staticmethod
    def findPos(template, image, threshold=None):
        res = cv2.matchTemplate(image, template, cv2.TM_SQDIFF_NORMED)
        h, w = template.shape[:2]

        if not threshold:
            lerror, herror, lpos, hpos = cv2.minMaxLoc(res)

            x, y = lpos
            return lerror, (x + w // 2, y + h // 2)
        else:
            loc = np.where(res <= threshold)

            return [(pos[0] + w // 2, pos[1] + h // 2) for pos in zip(*loc[::-1])]


class DiscordWebHook:
    def send(config, stats):
        if not (url := config(["webhook", "url"])):
            return

        post(url, json={
            "username": "Re:Twisted bot",
            # "avatar_url": "",
            "content": f"<@{config(['webhook', 'ping id'])}>" if config(['webhook', 'ping id']) else "",
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


class Gui:
    class PausePopUP:
        def __init__(self, parent, pausedE):
            self.root = tk.Toplevel(parent, background="red")
            self.root.withdraw()

            self.pausedE = pausedE

            self.setup()

        def setup(self):
            self.root.title("Re:Twisted - pop up")
            self.root.geometry("350x150")
            self.root.resizable(False, False)

            self.root.protocol("WM_DELETE_WINDOW", self.close)

            redFrame = tk.Frame(self.root)
            redFrame.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)

            frame = tk.Frame(redFrame)
            frame.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)

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

    class ScaleFactorPopup:
        def __init__(self, parent, name):
            self.root = tk.Toplevel(parent)
            self.root.withdraw()

            self.name = name

            self.setup()

        def open(self):
            self.root.deiconify()

        def setup(self):
            self.root.title("Re:Twisted - scale factor setup")
            self.root.geometry("450x170")
            self.root.resizable(False, False)

            self.root.protocol("WM_DELETE_WINDOW", sys.exit)

            frame = tk.Frame(self.root)
            frame.pack(padx=15, pady=15, fill=tk.BOTH, expand=True)

            tk.Label(frame, text="Wrong scale factor detected", font=(None, 16)).pack()
            tk.Label(frame, text=f"Detected an unsupported scale factor on the screen with {self.name}. Please change the scale to 100% in the settings to proceed.", font=(None, 12), wraplength=450).pack()
            
            buttons = tk.Frame(frame)
            buttons.pack(side=tk.BOTTOM, fill=tk.X)

            tk.Button(buttons, text="Settings", font=(None, 14), command=lambda: os.startfile("ms-settings:display")) \
                .pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            tk.Button(buttons, text="Exit", font=(None, 14), command=sys.exit) \
                .pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

    def __init__(self):
        self.root = tk.Tk()

        self.pausedE = threading.Event()
        self.pausedE.pause = self.pause
        self.pausedE.unpause = self.unpause

        self.config = Config(self.root, self.copyReportToClipboard)
        self.popup = self.PausePopUP(self.root, self.pausedE)
        self.ihandler = InputHandler(self.pausedE)

        self.setup()

        self.games = []
        self.detectGames()

        self.updateHisotry()

        self.root.mainloop()

    def detectGames(self):
        for className in Game.CLASSNAMES.keys():
            if (win := win32gui.FindWindow(className, "Roblox")) != 0:
                self.games.append(Game(
                    win,
                    self.right_side_SF,
                    self.ihandler,
                    self.config.getSetting,
                    self.handleData,
                    self.pausedE,
                    server=(len(self.games) + 1)
                ))

        if not len(self.games):
            frame = tk.Frame(self.right_side_SF, width=470, height=500)
            frame.pack_propagate(False)
            frame.pack(padx=5, pady=5)
            tk.Label(frame, text="No Roblox detected", font=(None, 20)).pack(side=tk.TOP, pady=(10, 0))
            tk.Label(frame, text="Make sure you have started Roblox before Re:Twisted", wraplength=470) \
                .pack(side=tk.TOP, pady=(10, 0))
            tk.Button(frame, text="Restart", 
                      command=lambda: os.execl(sys.executable, sys.executable, * sys.argv), 
                      background="red", activebackground="red") \
                .pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

    def handleData(self, stats):
        cape = stats["FORECAST"]["CAPE"]

        if cape >= (high := self.config.getSetting(["cape", "highest"])) and high != 0 or \
           cape <= (low := self.config.getSetting(["cape", "lowest"])) and low != 0:
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
        self.root.defaultFont.configure(family="Comic Sans MS", size=16)

        lbg = "#ccc"
        self.left_side = tk.Frame(self.root, width=350, background=lbg)
        self.left_side.pack(side=tk.LEFT, fill=tk.BOTH)
        self.left_side.pack_propagate(False)

        self.right_side = tk.Frame(self.root, width=500)
        self.right_side.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.right_side.pack_propagate(False)

        tk.Label(self.left_side, text="Re:Twisted", font=(None, 20), background=lbg) \
            .pack(side=tk.TOP)

        tk.Label(self.left_side, text=f"version {VERSION}", font=(None, 12), background=lbg) \
            .pack(side=tk.TOP, pady=(0, 15))

        self.status = tk.Label(self.left_side, text="Status - Paused", background=lbg)
        self.status.pack(side=tk.TOP)

        server_buttons = tk.Frame(self.left_side, background=lbg)
        server_buttons.pack(fill=tk.X, side=tk.TOP)
        tk.Button(server_buttons, text="Start", command=self.unpause) \
            .pack(fill=tk.X, side=tk.LEFT, anchor=tk.N, pady=5, padx=5, expand=True)
        tk.Button(server_buttons, text="Pause", command=self.pause) \
            .pack(fill=tk.X, side=tk.RIGHT, anchor=tk.N, pady=5, padx=5, expand=True)

        tk.Button(self.left_side, text="Settings", command=self.config.open) \
            .pack(fill=tk.X, side=tk.TOP, pady=5, padx=5)

        tk.Label(self.left_side, text="Records", background=lbg) \
            .pack(side=tk.TOP)

        left_sf_canvas = tk.Canvas(self.left_side)
        self.left_side_SF = tk.Frame(left_sf_canvas)

        scrollbar = tk.Scrollbar(self.left_side, orient=tk.VERTICAL, command=left_sf_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5, padx=(0, 5))
        left_sf_canvas.configure(yscrollcommand=scrollbar.set)

        left_sf_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=(5, 0))
        left_sf_canvas.create_window((0, 0), window=self.left_side_SF, anchor=tk.NW)

        self.left_side_SF.bind("<Configure>", \
                               lambda event, canvas=left_sf_canvas: canvas.configure(scrollregion=canvas.bbox("all")))

        self.recordsUpdateCallbacks = []
        for recordType, command in [
            ["Highest cape", lambda timeHistory, capeHistory: f"{max(capeHistory)} J/kg" if capeHistory else None],
            ["Lowest cape", lambda timeHistory, capeHistory: f"{min(capeHistory)} J/kg" if capeHistory else None],
            ["Average cape", lambda timeHistory, capeHistory: f"{round(sum(capeHistory) / len(capeHistory))} J/kg" if capeHistory else None],
            ["Avg reroll time", lambda timeHistory, capeHistory: f"{round(sum(timeHistory) / len(timeHistory), 1)} sec" if timeHistory else None],
            ["Rerolls per hour", lambda timeHistory, capeHistory: f"{round(len(self.games) * (3600 / (sum(timeHistory) / len(timeHistory))))} rph" if timeHistory else None],
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
        right_sf_canvas.create_window((0, 0), window=self.right_side_SF, anchor=tk.NW)

        self.right_side_SF.bind("<Configure>", \
                                lambda event, canvas=right_sf_canvas: canvas.configure(scrollregion=canvas.bbox("all")))

    def copyReportToClipboard(self):
        out = []
        out.append("# System Stats")
        out.append(f"[OS][{platform.platform()}]")

        out.append("# Re:twisted")
        out.append(f"[Version][{VERSION}]")
        out.append(f"[Paused][{not self.pausedE.is_set()}]")
        out.append(f"[Discord Webhook URL][{bool(self.config.getSetting(['webhook', 'url']))}]")
        out.append(f"[Discord Ping ID][{self.config.getSetting(['webhook', 'ping id'])}]")
        out.append(f"[Tesseract][{Tesseract.testTesseract()}]")

        out.append("# Input handler")
        out.append(f"[Queue size][{len(self.ihandler.eventsQueue)}]")
        out.append(f"[Actions][{self.ihandler.counter}]")
        out.append(f"[Is alive][{self.ihandler.is_alive()}]")

        out.append("# Games")
        for game in self.games:
            out.append(f"## {game.getName()}")
            out.append(f"[Paused][{not game.lPaused.is_set()}]")
            out.append(f"[Status][{game.status}]")
            out.append(f"[Server][{game.server}]")
            out.append(f"[Rolled servers][{len(game.history)}]")
            out.append(f"[Is alive][{game.is_alive()}]")

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText("```md\n%s\n```" % "\n".join(out))
        win32clipboard.CloseClipboard()

    @staticmethod
    def coppiedButton(button, text, func):
        button.config(text="Copied")
        func()
        button.after(500, lambda: button.config(text=text))


class Config:
    TEMPLATE = {
        "webhook": {
            "url": [str, "",
                    "Webhook url where message will be sent on successful find.\nLeave empty for no message."],
            "ping id": [str, "",
                        "User / Role which will be pinged in message."]
        },
        "cape": {
            "highest": [int, 7000,
                        "Will stop rolling, if it's over this number.\nEntring 0 will disable this feature."],
            "lowest": [int, 300,
                       "Will stop rolling, if it's under this number.\nEntring 0 will disable this feature."]
        },
        "timeout": [int, 120, "Maximum amount of time that the server can take to reroll.\nEntring 0 will disable timeout feature."],
        "tesseract path": [str, "C:\\Program Files\\Tesseract-OCR\\tesseract.exe", "Path to Tesseract executable for OCR to work."]
    }

    CONFIG_FILE = ".config.json"

    def __init__(self, parent, copyReportToClipboard):
        self.root = tk.Toplevel(parent)
        self.root.withdraw()

        self.copyReportToClipboard = copyReportToClipboard

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

        debugBtn = tk.Button(self.root, text="Copy debug info",
                             command=lambda: Gui.coppiedButton(debugBtn, "Copy debug info", self.copyReportToClipboard))
        debugBtn.pack(fill=tk.X, side=tk.BOTTOM, pady=5, padx=5)

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
        canvas.create_window((0, 0), window=frame, anchor=tk.NW)

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

            tk.Label(frame, text=last).pack(anchor=tk.W)
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

                tk.Label(frame, state=tk.DISABLED, text=template[2], font=(None, 10), anchor=tk.W, justify=tk.LEFT) \
                    .pack(fill=tk.X, side=tk.TOP, padx=(3, 0))

                tk.Entry(frame, textvariable=inpt, width=50) \
                    .pack(pady=(0, 15), side=tk.LEFT, padx=(3, 0))

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
                return {key: Config.fitDictToDict(item, config, path=path + [key]) \
                        for key, item in template.items()}
            case list():
                conf = Config.getInDict(config, path)
                return Config.defaultIfInvalid(conf, template[0], template[1])


class Tesseract:
    TESERACT_CONFIG = ["tesseract path"]
    
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

        self.pathVar = tk.StringVar(value=self.getSetting(self.TESERACT_CONFIG))

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
        pytesseract.pytesseract.tesseract_cmd = self.getSetting(self.TESERACT_CONFIG)

        if not self.testTesseract():
            self.open()

    def open(self):
        self.pathVar.set(self.getSetting(self.TESERACT_CONFIG))
        self.root.deiconify()

    def close(self, save=False):
        self.root.withdraw()

        path = self.pathVar.get()
        if save and path:
            self.setSetting(self.TESERACT_CONFIG, path)
            self.loadTesseract()

    @staticmethod
    def testTesseract():
        try:
            pytesseract.get_tesseract_version()
            return True
        except:
            return False


if __name__ == '__main__':
    Gui()
