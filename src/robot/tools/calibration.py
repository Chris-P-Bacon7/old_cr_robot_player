import cv2
import numpy as np
import time
import keyboard
import json
import os
from src.robot.perception.window_capture import WindowCapture 

# ================= CONFIGURATION =================
WINDOW_NAME = "Clash Royale - ZiqPlayz" 
ARENA_WIDTH = 18
ARENA_HEIGHT = 30
# =================================================

# --- VISUALIZATION HELPERS ---
def draw_perspective_grid(img, corners, show_inner_grid=True):
    h, w = img.shape[:2]
    
    # Source: The logical 18x32 grid corners (Still edges for calibration)
    src_points = np.float32([[0, 0], [ARENA_WIDTH, 0], [0, ARENA_HEIGHT], [ARENA_WIDTH, ARENA_HEIGHT]])
    dst_points = np.float32(corners)
    
    # Calculate transform matrix
    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    
    def tile_to_pixel(tx, ty):
        point = np.array([[[tx, ty]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point, matrix)
        return (int(transformed[0][0][0]), int(transformed[0][0][1]))

    # Draw Frame (Always visible - Represents the Edges 0-18)
    tl, tr = tile_to_pixel(0, 0), tile_to_pixel(ARENA_WIDTH, 0)
    bl, br = tile_to_pixel(0, ARENA_HEIGHT), tile_to_pixel(ARENA_WIDTH, ARENA_HEIGHT)
    
    cv2.line(img, tl, tr, (0, 255, 0), 2) 
    cv2.line(img, tr, br, (0, 255, 0), 2) 
    cv2.line(img, br, bl, (0, 255, 0), 2) 
    cv2.line(img, bl, tl, (0, 255, 0), 2) 

    if show_inner_grid:
        # <--- KEY CHANGE: Draw lines at Tile Centers (0.5, 1.5, etc) --->
        # Vertical Center Lines
        for x in range(ARENA_WIDTH):
            center_x = x + 0.5
            p1 = tile_to_pixel(center_x, 0)
            p2 = tile_to_pixel(center_x, ARENA_HEIGHT)
            
            # Highlight the middle lane (Center of tile 9)
            color = (50, 200, 200) if x == 9 else (100, 100, 100) 
            cv2.line(img, p1, p2, color, 1)

        # Horizontal Center Lines
        for y in range(ARENA_HEIGHT):
            center_y = y + 0.5
            p1 = tile_to_pixel(0, center_y)
            p2 = tile_to_pixel(ARENA_WIDTH, center_y)
            
            # Highlight the river area (Center of tile 18 is usually river/bridge)
            color = (50, 50, 255) if y == 15 else (100, 100, 100)
            cv2.line(img, p1, p2, color, 1)
        
    return img

def main():
    cap = WindowCapture(WINDOW_NAME)
    
    print("Waiting for window...")
    while True:
        frame = cap.get_screenshot()
        if frame is not None: break
        time.sleep(1)

    h, w = frame.shape[:2]
    print(f"Calibration Resolution: {w}x{h}") 
    
    # --- 1. ARENA (PERSPECTIVE) ---
    top_margin = int(w * 0.12)
    bot_margin = int(w * 0.04)
    top_y = int(h * 0.12)
    bot_y = int(h * 0.82)
    
    arena_pts = [
        [top_margin, top_y],            # TL
        [w - top_margin, top_y],        # TR
        [bot_margin, bot_y],            # BL
        [w - bot_margin, bot_y]         # BR
    ]
    
    # --- 2. CARD SLOTS ---
    card_y = int(h * 0.90)
    card_spread = int(w / 4.5)
    start_x = int(w / 2) - int(card_spread * 1.5)
    card_pts = [
        [start_x, card_y], [start_x + card_spread, card_y],
        [start_x + card_spread*2, card_y], [start_x + card_spread*3, card_y]
    ]

    # --- 3. ELIXIR BAR (RECTANGLE) ---
    elixir_tl = [int(w * 0.25), int(h * 0.96)]
    elixir_br = [int(w * 0.75), int(h * 0.99)]
    elixir_rect_pts = [elixir_tl, elixir_br] 

    modes = ["ARENA (3D)", "CARDS", "ELIXIR (2D)"]
    current_mode = 0
    active_idx = 0
    show_grid = True 
    
    print("\n--- CONTROLS ---")
    print("SPACE:  Switch Mode")
    print("TAB:    Select Corner")
    print("G:      Toggle Grid Lines")
    print("ARROWS: Move Corner (Shift for speed)")
    print("ENTER:  Save & Quit")

    cv2.namedWindow("Calibration Wizard", cv2.WINDOW_NORMAL)
    
    window_size = input("What window size would you like (small/large): ")
    if window_size.lower() == "large":
        cv2.resizeWindow("Calibration Wizard", 450, 954)
    else:
        cv2.resizeWindow("Calibration Wizardw", 375, 800)

    while True:
        frame = cap.get_screenshot()
        if frame is None: continue
        
        # --- INPUT ---
        if keyboard.is_pressed('space'):
            current_mode = (current_mode + 1) % 3
            active_idx = 0
            time.sleep(0.3)
            
        if keyboard.is_pressed('tab'):
            limit = 2 if current_mode == 2 else 4
            active_idx = (active_idx + 1) % limit
            time.sleep(0.2)
            
        if keyboard.is_pressed('g'):
            show_grid = not show_grid
            time.sleep(0.2)

        speed = 4 if keyboard.is_pressed('shift') else 1 
        
        # Select Target
        if current_mode == 0: target = arena_pts
        elif current_mode == 1: target = card_pts
        elif current_mode == 2: target = elixir_rect_pts

        if keyboard.is_pressed('up'):    target[active_idx][1] -= speed
        if keyboard.is_pressed('down'):  target[active_idx][1] += speed
        if keyboard.is_pressed('left'):  target[active_idx][0] -= speed
        if keyboard.is_pressed('right'): target[active_idx][0] += speed

        # --- DRAWING ---
        if current_mode == 0:
            frame = draw_perspective_grid(frame, arena_pts, show_inner_grid=show_grid)
            cv2.circle(frame, tuple(arena_pts[active_idx]), 3, (0, 255, 0), -1)
            cv2.putText(frame, "Align OUTER box to Arena Corners", (20, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            pts = np.array(arena_pts, np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (50, 50, 50), 1)

        if current_mode == 1:
            for i, pt in enumerate(card_pts):
                color = (0, 255, 0) if i == active_idx else (0, 255, 255)
                cv2.circle(frame, tuple(pt), 4, color, 1)
                cv2.circle(frame, tuple(pt), 1, color, -1)
        elif current_mode != 1:
             for pt in card_pts: cv2.circle(frame, tuple(pt), 2, (0, 100, 100), -1)

        e_tl = elixir_rect_pts[0]
        e_br = elixir_rect_pts[1]
        cv2.rectangle(frame, tuple(e_tl), tuple(e_br), (255, 0, 255), 1)
        
        if current_mode == 2:
            cv2.circle(frame, tuple(elixir_rect_pts[active_idx]), 3, (0, 255, 0), -1)
        
        cv2.putText(frame, f"MODE: {modes[current_mode]}", (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Calibration Wizard", frame)
        if cv2.waitKey(1) == 13: break 
        if keyboard.is_pressed('q'): exit()

    cv2.destroyAllWindows()

    # --- SAVE ---
    ex_full = [e_tl, [e_br[0], e_tl[1]], [e_tl[0], e_br[1]], e_br]
    
    config_data = {
        "arena": {
            "top_left": arena_pts[0], "top_right": arena_pts[1],
            "bottom_left": arena_pts[2], "bottom_right": arena_pts[3]
        },
        "card_slots": {
            "card_1": card_pts[0], "card_2": card_pts[1],
            "card_3": card_pts[2], "card_4": card_pts[3]
        },
        "elixir": {
            "top_left": ex_full[0], "top_right": ex_full[1],
            "bottom_left": ex_full[2], "bottom_right": ex_full[3]
        }
    }

    save_path = input("\nEnter the path/filename to save the config to (e.g., bot_config.json) or leave empty to skip saving: ").strip()
    
    if save_path:
        if os.path.exists(save_path):
            with open(save_path, "r") as f:
                try: current_data = json.load(f)
                except json.JSONDecodeError: current_data = {} 
        else: current_data = {}

        current_data.update(config_data)

        with open(save_path, "w") as f:
            json.dump(current_data, f, indent=4)
        print(f"✅ Configuration Updated in {save_path}!")
    else:
        print("Skipped saving configuration.")

if __name__ == "__main__":
    main()