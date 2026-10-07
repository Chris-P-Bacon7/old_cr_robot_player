from ultralytics import YOLO
from src.robot.tools.json_worker import JsonWorker
import cv2


class GameState:
    def __init__(self, device_json_name, device_json_location, db_json_name, db_json_location, 
                 screen_mapper, model_path="runs\\detect\\train7\\weights\\best.pt"): 
        self.json_worker = JsonWorker(db_json_location, db_json_name)
        self.config = self.json_worker.config_json_coord(device_json_location, device_json_name)
        self.data = self.json_worker.load_json(db_json_location, db_json_name)
        
        self.screen_mapper = screen_mapper

        self.model = YOLO(model_path)
        self.names = self.model.names
        
    def detect_threats(self, detections, names_map):
        threats = []
        for box in detections:
            x1, y1, x2, y2 = box.xyxy[0]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])

            if cls_id not in names_map: continue
            raw_name = names_map[cls_id]
            if "-" not in raw_name: continue

            name_parts = raw_name.split("-")
            team = name_parts[0]
            troop = name_parts[1]

            # Grab everything from index 2 onwards. If it doesn't exist, it safely returns an empty list []
            state = name_parts[2:] if len(name_parts) > 2 else None

            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            tile_x, tile_y = self.screen_mapper.pixel_to_tile(cx, cy)

            if team == "Enemy" and troop not in ("PrincessTower", "KingTower"):
                threats.append({"Troop": troop, "x": cx, "y": cy, 
                                "tile_x": tile_x, "tile_y": tile_y, "conf": conf, "state": state})
            
            threats.sort(key=lambda t: t["tile_y"], reverse=True)
        return threats

    def evaluate_threats(self, threats):
        if not threats:
            return []
        
        final_evaluation = []

        tower_y = 24.0

        w_urgency = 1.5
        w_power = 2.0
        
        for threat in threats:
            enemy_name = threat["Troop"]
            enemy_data = self.data["cards"].get(enemy_name, {})

            # 1. Calculate urgency
            speed_unit = enemy_data.get("speed", 60)
            tiles_per_sec = speed_unit * 0.02

            distance = max(tower_y - threat["tile_y"], 0)
            eta = distance / tiles_per_sec

            urgency_eval = 10.0 / (eta + 1.0)

            # 2. Calculate importance
            elixir = enemy_data.get("elixir", 3)
            card_class = enemy_data.get("class", "").lower()

            if card_class == "wincon":
                class_multiplier = 2.0
            elif card_class == "tank":
                class_multiplier = 1.5
            elif card_class == "mini":
                class_multiplier = 0.25
            else:
                class_multiplier = 1.0
            
            power_eval = elixir * class_multiplier

            # 3. Apply weights
            evaluation = (w_urgency * urgency_eval) + (w_power * power_eval)

            threat["threat_score"] = evaluation
            threat["eta"] = eta
            
            final_evaluation.append(threat)

        final_evaluation.sort(key=lambda t: t["threat_score"], reverse=True)

        return final_evaluation
    