import pyautogui
import time
import random
import keyboard

# Next steps: Implement drag and click and Bezier curves to bypass bot detection

pyautogui.FAILSAFE = True

class GameController:
    def __init__(self, window_capture):
        self.cap = window_capture
        # This is the width the bot "thinks" the world is (from your calibration)
        self.reference_width = 500.0 

    def _get_global_coords(self, game_x, game_y):
        if self.cap.monitor is None:
            if not self.cap.update_window_position():
                print("❌ Controls Error: Window not found!")
                return None, None

        # --- SCALING FIX ---
        # Calculate how much bigger/smaller the real window is compared to the bot's vision
        current_width = self.cap.monitor["width"]
        scale_factor = current_width / self.reference_width
        
        # Scale the coordinates
        scaled_x = game_x * scale_factor
        scaled_y = game_y * scale_factor

        screen_x = self.cap.monitor["left"] + scaled_x
        screen_y = self.cap.monitor["top"] + scaled_y
        
        return screen_x, screen_y

    def click(self, game_x, game_y):
        sx, sy = self._get_global_coords(game_x, game_y)
        if sx is None: return

        duration = random.uniform(0.05, 0.15) 
        pyautogui.moveTo(sx, sy, duration=duration)
        pyautogui.click()

    def play_card(self, card_key, tile_target, screen_config, mapper):
        if card_key not in screen_config:
            print(f"❌ Error: {card_key} not found in config!")
            return

        card_x, card_y = screen_config[card_key]
        self.click(card_x, card_y)

        tx, ty = tile_target
        field_x, field_y = mapper.tile_to_pixel(tx, ty)
        
        sx, sy = self._get_global_coords(field_x, field_y)
        if sx:
            pyautogui.moveTo(sx, sy, duration=random.uniform(0.10, 0.20))

        pyautogui.click()
        time.sleep(0.1)
        
    def get_active_key(valid_keys):
        for key in valid_keys:
            if keyboard.is_pressed(key):
                return key
        return None