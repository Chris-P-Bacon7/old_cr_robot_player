import numpy as np
import mss
import pygetwindow as gw
import cv2
import json
import os

class WindowCapture:
    def __init__(self, window_title_keyword, json_file="bot_config.json"):
        self.window_title = window_title_keyword
        self.json_save = json_file
        self.monitor = None
        self.sct = mss.mss()
        self.config_path_prompted = False
        self.config_save_path = ""
        self.update_window_position()

    def update_window_position(self):
        windows = gw.getWindowsWithTitle(self.window_title)
        
        if not windows:
            print(f"❌ Error: Window '{self.window_title}' not found!")
            self.monitor = None
            return False

        win = windows[0]
        
        # Define the capture area (skip title bar)
        title_bar_height = 60
        fgm_width = 20
        fgm_height = 8

        self.monitor = {
            "top": win.top + title_bar_height, 
            "left": win.left + fgm_width // 2, 
            "width": win.width - fgm_width, 
            "height": win.height - title_bar_height - fgm_height
        }
        
        # Save window position to config
        self._save_window_config()
        return True

    def _save_window_config(self):
        new_data = {"window": self.monitor}
        if os.path.exists(self.json_save):
            with open(self.json_save, "r") as f:
                try: current = json.load(f)
                except: current = {}
        else: current = {}
        
        current.update(new_data)
        with open(self.json_save, "w") as f:
            json.dump(current, f, indent=4)

    def get_screenshot(self):
        if self.monitor is None:
            if not self.update_window_position():
                return None

        # Capture Raw Image
        screenshot = self.sct.grab(self.monitor)
        img = np.array(screenshot)
        img = img[:, :, :3] # Drop Alpha
        img = np.ascontiguousarray(img)

        target_width = 500
        
        scale = target_width / img.shape[1] 
        dim = (target_width, int(img.shape[0] * scale))
        
        # INTER_AREA is the best resizing method for shrinking (keeps it sharp)
        resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

        return resized