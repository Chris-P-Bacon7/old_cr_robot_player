import numpy as np
import cv2

class ScreenMapper:
    def __init__(self, config, arena_height, arena_width):
        self.src_points = np.float32([[0, 0], [arena_width, 0], [0, arena_height], [arena_width, arena_height]])
        self.dst_points = np.float32([
            config["arena_top_left"], config["arena_top_right"], 
            config["arena_bottom_left"], config["arena_bottom_right"]
        ])
        self.matrix = cv2.getPerspectiveTransform(self.src_points, self.dst_points)

    def tile_to_pixel(self, tile_x, tile_y):
        point = np.array([[[tile_x, tile_y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point, self.matrix)
        return (int(transformed[0][0][0]), int(transformed[0][0][1]))
    
    def pixel_to_tile(self, px, py):
        inv_matrix = np.linalg.inv(self.matrix)
        point = np.array([[[px, py]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point, inv_matrix)

        tile_x = transformed[0][0][0]
        tile_y = transformed[0][0][1]
        
        return (tile_x, tile_y)