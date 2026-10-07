import cv2
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import time
from src.robot.perception.window_capture import WindowCapture


class WindowCoordinateGatherer:
    def __init__(self, window_name="SM-S936W"):
        self.window_name = window_name
        self.cap = WindowCapture(self.window_name, "robot\\Chris_S25.json")
        
        print(f"Waiting for window: '{self.window_name}'...")
        while True:
            frame = self.cap.get_screenshot()
            if frame is not None: 
                break
            time.sleep(1)
            
        print("Window found! Starting tool...")
        
        # Tools: 0 = Rectangle, 1 = Grid, 2 = Dots
        self.tools = ["Rectangle", "Grid", "Dots"]
        self.current_tool_idx = 0
        
        # --- Shared State ---
        self.drawing = False
        
        # --- Rectangle State ---
        self.rect_start = None
        self.rect_end = None
        
        # --- Grid State ---
        self.grid_start = None
        self.grid_end = None
        self.grid_rows = 3
        self.grid_cols = 3
        self.grid_edit_mode = "Rows"
        
        # --- Dots State ---
        self.dots = []
        
        self.ui_window = "Live Coordinate Gatherer"
        cv2.namedWindow(self.ui_window, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.ui_window, self.mouse_events)

    def mouse_events(self, event, x, y, flags, param):
        if self.current_tool_idx == 0:  # RECTANGLE
            if event == cv2.EVENT_LBUTTONDOWN:
                self.drawing = True
                self.rect_start = (x, y)
                self.rect_end = (x, y)
            elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
                self.rect_end = (x, y)
            elif event == cv2.EVENT_LBUTTONUP:
                self.drawing = False
                self.rect_end = (x, y)

        elif self.current_tool_idx == 1:  # GRID
            if event == cv2.EVENT_LBUTTONDOWN:
                self.drawing = True
                self.grid_start = (x, y)
                self.grid_end = (x, y)
            elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
                self.grid_end = (x, y)
            elif event == cv2.EVENT_LBUTTONUP:
                self.drawing = False
                self.grid_end = (x, y)

        elif self.current_tool_idx == 2:  # DOTS
            if event == cv2.EVENT_LBUTTONDOWN:
                self.dots.append((x, y))

    def run(self):
        while True:
            # 1. Grab live frame directly from the window
            frame = self.cap.get_screenshot()
            if frame is None:
                continue
                
            tool_name = self.tools[self.current_tool_idx]

            # 2. Draw active overlays
            if self.current_tool_idx == 0 and self.rect_start and self.rect_end:
                cv2.rectangle(frame, self.rect_start, self.rect_end, (0, 255, 0), 2)

            elif self.current_tool_idx == 1 and self.grid_start and self.grid_end:
                cv2.rectangle(frame, self.grid_start, self.grid_end, (255, 0, 0), 2)
                x1, y1 = self.grid_start
                x2, y2 = self.grid_end
                
                x_min, x_max = min(x1, x2), max(x1, x2)
                y_min, y_max = min(y1, y2), max(y1, y2)
                
                if self.grid_rows > 1:
                    row_step = (y_max - y_min) // self.grid_rows
                    for i in range(1, self.grid_rows):
                        cv2.line(frame, (x_min, y_min + i * row_step), (x_max, y_min + i * row_step), (255, 100, 0), 1)
                
                if self.grid_cols > 1:
                    col_step = (x_max - x_min) // self.grid_cols
                    for i in range(1, self.grid_cols):
                        cv2.line(frame, (x_min + i * col_step, y_min), (x_min + i * col_step, y_max), (255, 100, 0), 1)

            elif self.current_tool_idx == 2:
                for idx, pt in enumerate(self.dots):
                    cv2.circle(frame, pt, 5, (0, 0, 255), -1)
                    cv2.putText(frame, str(idx+1), (pt[0]+8, pt[1]-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)

            # 3. HUD Overlay
            cv2.putText(frame, f"Tool: {tool_name} (Space to switch)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "Enter: Save & Return | Q: Quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            if self.current_tool_idx == 0:
                cv2.putText(frame, "Tab: Clear Rectangle", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            elif self.current_tool_idx == 1:
                cv2.putText(frame, f"Tab: Editing [{self.grid_edit_mode}] | W/S: Change count", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 150, 0), 2)
                cv2.putText(frame, f"Rows: {self.grid_rows} | Cols: {self.grid_cols}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 150, 0), 2)
            elif self.current_tool_idx == 2:
                cv2.putText(frame, "Tab: Undo last dot", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 150, 255), 2)

            # 4. Render
            cv2.imshow(self.ui_window, frame)
            
            # 5. Keybinds
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'): 
                cv2.destroyAllWindows()
                return None
            elif key == 32: # SPACE
                self.current_tool_idx = (self.current_tool_idx + 1) % len(self.tools)
            elif key == 9: # TAB
                if self.current_tool_idx == 0: self.rect_start, self.rect_end = None, None
                elif self.current_tool_idx == 1: self.grid_edit_mode = "Cols" if self.grid_edit_mode == "Rows" else "Rows"
                elif self.current_tool_idx == 2: 
                    if self.dots: self.dots.pop()
            elif key == ord('w'):
                if self.current_tool_idx == 1:
                    if self.grid_edit_mode == "Rows": self.grid_rows += 1
                    else: self.grid_cols += 1
            elif key == ord('s'):
                if self.current_tool_idx == 1:
                    if self.grid_edit_mode == "Rows": self.grid_rows = max(1, self.grid_rows - 1)
                    else: self.grid_cols = max(1, self.grid_cols - 1)
            elif key == 13 or key == 10: # ENTER
                cv2.destroyAllWindows()
                if self.current_tool_idx == 0:
                    return {"tool": "rectangle", "coords": (self.rect_start, self.rect_end)}
                elif self.current_tool_idx == 1:
                    return {"tool": "grid", "bounds": (self.grid_start, self.grid_end), "rows": self.grid_rows, "cols": self.grid_cols}
                elif self.current_tool_idx == 2:
                    return {"tool": "dots", "coords": self.dots}

if __name__ == "__main__":
    # Uses the same default window name as your calibration script
    tool = WindowCoordinateGatherer()
    results = tool.run()
    
    print("\n--- Gathered Coordinates ---")
    print(results)