import cv2
import numpy as np
import json
import os

class CardVision:
    def __init__(self):
        self.templates = {}

    def load_template(self, name, image_path, evo_hero):
        """
        Loads an image file (like 'hog_rider.png') into memory.
        """
        filename = f"Card_{name}"

        if evo_hero == 1:
            filename = f"Card_{name}_Evo"
        elif evo_hero == 2:
            filename = f"Card_{name}_Hero"
        
        filename = f"{filename}.png"
        full_path = os.path.join(image_path, filename)
        
        img = cv2.imread(full_path, cv2.IMREAD_COLOR)
        
        if img is None:
            print(f"Error: Could not find image at '{image_path}'")
        else:
            if name not in self.templates:
                self.templates[name] = []
            
            self.templates[name].append(img)
            print(f"- Learned pattern: {name}, {full_path}")
    

    def find(self, haystack_img, template_name, threshold, debug_mode=False):
        """
        Scans the 'haystack' (screenshot) for the 'template'.
        Returns: A list of Rectangles (x, y, w, h) where matches were found.
        """
        if template_name not in self.templates:
            return []

        frame = cv2.cvtColor(haystack_img, cv2.COLOR_BGR2GRAY)

        all_matches = []

        for needle_img in self.templates[template_name]:
            for scale in [1.0, 1.18]: # Check slightly smaller, normal, and slightly larger
                width = int(needle_img.shape[1] * scale)
                height = int(needle_img.shape[0] * scale)
                resized_needle = cv2.resize(needle_img, (width, height))
                
                template = cv2.cvtColor(resized_needle, cv2.COLOR_BGR2GRAY)
                result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)

                locations = np.where(result >= threshold)
                locations = list(zip(*locations[::-1]))
                
                rectangles = []
                for loc in locations:
                    rect = [int(loc[0]), int(loc[1]), width, height]

                    rectangles.append(rect)
                    rectangles.append(rect)

                rectangles, weights = cv2.groupRectangles(rectangles, groupThreshold=1, eps=0.5)

                for (x, y, w, h) in rectangles:
                    try:
                        confidence = result[int(y), int(x)]
                    except IndexError:
                        confidence = 0

                    all_matches.append(((x, y, w, h), confidence))

        return all_matches