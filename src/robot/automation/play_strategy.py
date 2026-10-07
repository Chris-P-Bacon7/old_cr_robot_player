from src.robot.automation.game_state import GameState
import time
import pytesseract
import cv2

pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

class PlayStrategy:
    def __init__(self, roi_coordinates):
        self.opponent_elixir = 0
        self.last_time = 0
        self.full_elixir = 2.8
        self.roi_coordinates = roi_coordinates
        
        self.overtime = False
        self.overtime_countdown = 0
        
        self.initialized = False
    
    def parse_time_to_seconds(self, time_str):
        if not time_str or ":" not in time_str:
            return None
        
        try:
            minutes, seconds = time_str.split(':')
            total_seconds = (int(minutes) * 60) + int(seconds)
            return total_seconds
        except ValueError:
            return None

    def get_match_time(self, frame):
        x1, y1, x2, y2 = self.roi_coordinates
        timer_crop = frame[y1:y2, x1:x2]
        
        gray = cv2.cvtColor(timer_crop, cv2.COLOR_BGR2GRAY)
        
        resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(resized, 150, 255, cv2.THRESH_BINARY)
        
        custom_config = r"--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789:"
        
        raw_text = pytesseract.image_to_string(thresh, config=custom_config).strip()
        
        return self.parse_time_to_seconds(raw_text)

    def enemy_hand(self, detections):
        pass

    # def enemy_elixir(self, frame, detections):
    #     if self.get_match_time(frame) >= 170 and not self.initialized:
    #         self.opponent_elixir = 5 + (180 - self.get_match_time(frame)) / 2.8
    #         self.initialized = True
    #     elif self.get_match_time(frame) <= 60 and not self.overtime: 
    #         self.full_elixir = 1.4
    #     elif self.get_match_time(frame) <= 10 and not self.overtime:
    #         pass
    #     elif self.get_match_time(frame) <= 60 and self.overtime:
    #         self.full_elixir = 2.8 / 3
        
    #     self.opponent_elixir += (time.time() - self.last_time) / self.full_elixir
    
    #     self.last_time = time.time()
        
    #     return self.enemy_elixir