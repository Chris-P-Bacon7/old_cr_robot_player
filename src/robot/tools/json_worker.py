import json
import os

class JsonWorker:
    def __init__(self, json_location, json_name):
        self.json_location = json_location
        self.json_name = json_name
    
    def load_json(self, json_location, json_name):
        if not os.path.exists(json_location):
            print(f"ERROR: \"{json_name}\" not found.")
            return None
        with open(json_location, "r") as f:
            return json.load(f)

    def config_json_coord(self, json_location, json_name):
        if not os.path.exists(json_location):
            print(f"ERROR: \"{json_name}\" not found.")
            exit()
            
        with open(json_location, "r") as f:
            data = json.load(f)
            
        config = {}
        for k, v in data["arena"].items(): config[f"arena_{k}"] = tuple(v)
        for k, v in data["card_slots"].items(): config[k] = tuple(v)
        for k, v in data["elixir"].items(): config[f"elixir_{k}"] = tuple(v)
        return config
    
    