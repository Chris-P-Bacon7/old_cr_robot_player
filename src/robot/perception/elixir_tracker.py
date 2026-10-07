import cv2

class ElixirTracker:
    def __init__(self, config):
        self.config = config
        self.points = {}
        self.opponent_troops = []
        
        # Calculate the 10 points ONCE when the bot starts
        # This prevents doing math 60 times a second
        self._calculate_grid()

    def _calculate_grid(self):
        """
        Internal helper to map out the 10 elixir bubbles based on config.
        """
        # Safety Check: Ensure keys exist
        if "elixir_top_left" not in self.config:
            print("⚠️ Warning: Elixir coordinates missing from config.")
            return

        # 1. Get Coordinates
        left_x = self.config["elixir_top_left"][0]
        right_x = self.config["elixir_top_right"][0]
        
        top_y = self.config["elixir_top_left"][1]
        bottom_y = self.config["elixir_bottom_left"][1]

        # 2. Calculate Geometry
        # Width is Right - Left
        bar_width = right_x - left_x 
        middle_y = int((top_y + bottom_y) * 0.5)
        
        # Distance between bubbles (9 gaps for 10 bubbles)
        dx = bar_width / 9

        # 3. Store the 10 Points
        for i in range(1, 11):
            # Start at Left X.
            # (i - 1) ensures bubble #1 is at 0 distance.
            px = int(left_x + (i - 1) * dx)
            py = int(middle_y)
            
            self.points[i] = (px, py)

    def get_elixir(self, frame):
        """
        Checks the pre-calculated points.
        Returns the highest point that is purple.
        """
        current_elixir = 0
        
        try:
            h, w = frame.shape[:2]
        except AttributeError:
            return None

        # Loop through our pre-calculated points
        for i in range(1, 11):
            if i not in self.points:
                continue
                
            px, py = self.points[i]

            # Safety Check: Boundary
            if px >= w or py >= h:
                continue

            pixel = frame[py, px]

            # if i == 1:
            #     print(f"Elixir 1 Colour: {pixel}") # Check what colour the bot sees.

            if self.is_purple(pixel):
                current_elixir = i
            else:
                if i == 1:
                    gap = self.points[2][0] - self.points[1][0]
                    prev_x = self.points[1][0] - gap
                else:
                    prev_x = self.points[i - 1][0]
                
                cur_x = self.points[i][0]
                dx = (cur_x - prev_x) / 10.0

                fraction = 0.0

                for j in range(1, 10):
                    sub_x = int(prev_x + (dx * j))

                    if sub_x >= w:
                        continue
                    
                    sub_pixel = frame[py, sub_x]

                    if self.is_blue(sub_pixel):
                        fraction += 0.1

                return round(current_elixir + fraction, 3)

        return float(round(current_elixir, 3))
    
    def is_purple(self, pixel):
        """
        Helper function to determine if pixel is purple.
        Pixel is [Blue, Green, Red]
        """
        b, g, r = (int(pixel[0]), int(pixel[1]), int(pixel[2]))

        # Target Color (Pink/Purple)
        if r > 90 and b > 90: # Ensures that the colour is bright enough
            if r > (g + 15) and b > (g + 15):
                # Allows the colour to be super bright (glow) or purple
                # as long as it's not too bright or gray
                return True
            
        # Ensures that if the elixir bar is full but glowing, it is still valid
        if r > 220 and g > 220 and b > 220:
            return True
        
        return False
    
    def is_blue(self, pixel):
        """
        Detects the empty blue background of the elixir bar.
        Target RGB: (51, 80, 160) -> Target OpenCV BGR: [160, 80, 51]
        """
        b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])

        # 1. The Tolerance Window
        # We allow a +/- 30 margin around your target numbers to account for video blur
        if 130 < b < 190 and 50 < g < 110 and 20 < r < 80:
            
            # 2. The Ratio Check
            # Even if the numbers shift, it must maintain the core color profile: 
            # Blue is the strongest, Green is in the middle, Red is the weakest.
            if b > g and g > r:
                return True
                
        return False