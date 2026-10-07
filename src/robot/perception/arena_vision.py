from ultralytics import YOLO
import cv2

class ArenaVision:
    def __init__(self, model_path="runs\\detect\\train7\\weights\\best.pt"):
        print(f"Loading YOLO model from {model_path}...")

        try:
            self.model = YOLO(model_path)
            self.names = self.model.names
            print("Model successfully loaded.")
        except Exception as e:
            print(f"Failed to load model: {e}")
            exit()
        
    def find_troops(self, frame, threshold=0.75):
        # Convert BGR to RGB so YOLOv8 can read the screenshots properly
        # rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = list(self.model(frame, stream=False, conf=threshold, verbose=False))
        return results
    
    def draw_detections(self, frame, results):
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Get coordinates
                x1, y1, x2, y2, = box.xyxy[0]
                x1, y1, x2, y2, = int(x1), int(y1), int(x2), int(y2)

                # Get Class name and confidence
                cls_id = int(box.cls[0])
                cls_name = self.names[cls_id]
                conf = float(box.conf[0])

                # Determine colour
                colour = (0, 0, 255) # Enemy if red
                if "Player" in cls_name:
                    colour = (255, 0, 0)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)
                
                label = f"{cls_name} {int(conf*100)}%"
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 2)
        
        return frame