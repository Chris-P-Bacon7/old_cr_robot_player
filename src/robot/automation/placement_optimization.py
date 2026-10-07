import os
import sys
import math
import random as rand
import time

# Tell Python to look one folder up for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from src.robot.perception.screen_mapper import ScreenMapper
from src.robot.automation.game_state import GameState

class PlayAutomation:
    def __init__(self, cur_deck, arena_height=30, arena_width=18):
        self.arena_height = arena_height
        self.arena_width = arena_width
        self.crossed_bridge = arena_height * 0.45
        self.speed_multiplier = 0.02

        self.json_name = "card_database.json"
        self.json_location = f"robot\\{self.json_name}"
        self.device_json_name = "Chris_S25.json"
        self.device_json_location = f"robot\\{self.device_json_name}"

        self.deck = cur_deck
        self.data = self.load_json(self.json_location, self.json_name)
        self.counter_chart = self.config_json(self.data, "counters", cur_deck)
        self.card_info = self.config_json(self.data, "cards", cur_deck)
        self.screen_mapper = ScreenMapper(self.load_config("robot\\Chris_S25.json", "Chris_S25.json"), 30, 18)
        self.game_state = GameState(self.device_json_name, self.device_json_location, 
                                    self.json_name, self.json_location, self.screen_mapper)

        self.recent_plays = []

    def load_config(self, json_location, json_name):
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

    def load_json(self, json_location, json_name):
        """Loads the .json file for the counters of cards.

        Args:
            json_location (str): Relative path of the json
            json_name (str): your_json_name.json

        Returns:
            dict: Fully configured counter_chart
        """
        if not os.path.exists(json_location):
            print(f"ERROR: \"{json_name}\" not found.")
            exit()
        
        with open(json_location, "r") as f:
            data = json.load(f)

        return data
    
    def config_json(self, data, config_type, deck):
        """Following loading the .json file, organize info into
        respective dictionaries for easier processing.

        Args:
            data (dic): Raw dictionary from loaded .json file.
            config_type (str): Enter "counters", "cards" in separate calls.
            deck (list): Current deck being used.

        Returns:
            dict: Configured dictionary based on requested config_type.
        """
        if config_type == "cards":
            cards_info = {}
            for card in deck:
                cards_info[f"{card}"] = data["cards"][card]
            return cards_info
        else:
            chart = data[f"{config_type}"]
            return chart

    def calculate_optimal_placement(self, card_name, most_dangerous, latency_compensation=1.0):
        """
        Calculates the exact pixel coordinates to drop a card based on kinematics and unit offsets.
        Returns the formatted tuple required by the action thread.
        """
        enemy_name = most_dangerous["Troop"]
        enemy_data_full = self.data["cards"].get(enemy_name, {})
        card_class = self.card_info[card_name].get("class", "troop")
        
        enemy_x, enemy_y = most_dangerous["tile_x"], most_dangerous["tile_y"]

        # Shift target down for flying units so ground troops can actually hit them
        if "ability" in enemy_data_full and "air" in enemy_data_full["ability"]:
            enemy_y += 2.0

        if "spell" in card_class.lower():
            # Spell prediction math
            raw_speed_unit = self.card_info[card_name].get("speed", 800)
            tiles_per_sec = raw_speed_unit * 0.02

            enemy_speed_unit = enemy_data_full.get("speed", 0)
            enemy_tiles_per_sec = enemy_speed_unit * 0.02

            king_x, king_y = 9.0, 28.0

            # Calculate flight time from King Tower
            distance = ((enemy_x - king_x) ** 2 + (enemy_y - king_y) ** 2) ** 0.5
            flight_time = distance / tiles_per_sec
            total_spell_latency = 1.0 + flight_time

            play_x = enemy_x
            play_y = enemy_y + (total_spell_latency * enemy_tiles_per_sec)
            
        else:
            # Troop offset math
            enemy_speed_unit = enemy_data_full.get("speed", 0)
            enemy_tiles_per_sec = enemy_speed_unit * 0.02

            offset = self.card_info[card_name]["placement"]["offset"]

            # Pull them towards the center (Tile 9)
            if enemy_x >= 9: 
                play_x = enemy_x - (0.5 * offset ** 2) ** 0.5
            else: 
                play_x = enemy_x + (0.5 * offset ** 2) ** 0.5

            play_y = enemy_y + (0.5 * offset ** 2) ** 0.5 + (enemy_tiles_per_sec * (1.0 + latency_compensation))
            
        # Bound coordinates to ensure we don't click outside the arena
        play_x = max(0, min(play_x, self.arena_width))
        play_y = max(0, min(play_y, self.arena_height))

        # Convert mathematically perfect tile to physical screen pixels
        pixel_x, pixel_y = self.screen_mapper.tile_to_pixel(play_x, play_y)
        
        return (card_name, (pixel_x, pixel_y), most_dangerous)

    def get_defensive_move(self, evaluation, available_cards, current_elixir): # NEED LOGIC FOR CROSSED BRIDGE VS. NOT CROSSED
        most_dangerous = evaluation[0]
        enemy_name = most_dangerous["Troop"]

        # Prevent bot from overcommitting elixir on defense
        current_time = time.time()

        self.recent_plays = [p for p in self.recent_plays if current_time - p["time"] < 8.0]
        committed_elixir = 0
        for play in self.recent_plays:
            if abs(play["x"] - most_dangerous["tile_x"]) < 6.0:
                committed_elixir += play["elixir"]
        
        enemy_elixir = self.data["cards"].get(enemy_name, {}).get("elixir", 3)

        if committed_elixir >= (enemy_elixir - 1):
            return None

        if enemy_name not in self.counter_chart:
            print(f"LOGIC WARNING: No defined counter for {enemy_name}.")
            return None
        
        primary_counters = []
        primary_counters.extend(self.counter_chart[enemy_name].get("primary", []))
        primary_counters.extend(self.counter_chart[enemy_name].get("spell", []))
        primary_counters.extend(self.counter_chart[enemy_name].get("secondary", []))

        if most_dangerous.get("threat_score", 0) < 4.0:
            return None

        for card_name in primary_counters:
            if card_name in available_cards:
                cost = self.card_info[card_name]["elixir"]
                
                if current_elixir >= cost:
                    return self.calculate_optimal_placement(card_name, most_dangerous)
        return None
    
    def get_idle_move(self, available_cards, current_elixir, evaluation):
        """ 
        IMPROVEMENTS NEEDED:
        Check to make sure that the arena conditions are favourable
        before initiating an offensive decision 
        """
        if current_elixir < 4:
            return None
        elif 4 < current_elixir < 9:
            pass # This condition will check if a spell can be used to 
            # take out a unit next to the princess tower
        elif current_elixir > 9: 
            for card_name in available_cards:
                card_class = self.card_info[card_name].get("class", "").lower()
                cost = self.card_info[card_name]["elixir"]

                # 1. Iniitialize danger scores for both lanes
                left_danger = 0
                right_danger = 0
                for threat in evaluation:
                    danger_weight = threat.get("threat_score", 0)
                    
                    if threat["tile_x"] < 9.5:
                        left_danger += danger_weight
                    else:
                        right_danger += danger_weight

                # Make decision of which lane to be offensive in. Avoid lane with existing troops
                if left_danger > 10 or right_danger > 10:
                    break # If too dangerous, then we will place stuff in the back instead
                elif left_danger < right_danger:
                    lane_x = 2
                elif right_danger < left_danger:
                    lane_x = 16
                else:
                    lane_x = rand.choice([2, 16])
        
                if card_class == "wincon" and current_elixir >= cost:
                    pixel_x, pixel_y = self.screen_mapper.tile_to_pixel(lane_x, 14)

                    fake_enemy_data = {"Troop": "Offensive Push", "x": pixel_x, "y": pixel_y}
                    return (card_name, (pixel_x, pixel_y), fake_enemy_data)
            
            for card_name in available_cards:
                card_class = self.card_info[card_name].get("class", "").lower()
                if card_class != "tank" and "spell" not in card_class:
                    if left_danger > right_danger: lane_x = 9
                    else: lane_x = 10
                    pixel_x, pixel_y = self.screen_mapper.tile_to_pixel(lane_x, 30)
                    
                    return (card_name, (pixel_x, pixel_y), {"Troop": f"Cycle {card_name} in Back", "x": pixel_x, "y": pixel_y})

        return None

    def commit_play(self, card_name, tile_x, tile_y):
        self.recent_plays.append({
            "card": card_name,
            "time": time.time(),
            "x": tile_x,
            "y": tile_y,
            "elixir": self.card_info[card_name]["elixir"]
        })

    def get_best_move(self, detections, current_hand, current_elixir, names_map):
        """
        Main brain function.

        Args:
            detections: List of YOLO "box" objects
            current_hand: List of card names currently available
            current_elixir: Integer
        """
        available_cards = [card[0] for card in current_hand]

        threats = self.game_state.detect_threats(detections, names_map)
        evaluated_threats = self.game_state.evaluate_threats(threats)

        if evaluated_threats and evaluated_threats[0]["tile_y"] >= 8:
            move = self.get_defensive_move(evaluated_threats, available_cards, current_elixir)
            if move: return move
        elif not evaluated_threats or evaluated_threats[0]["tile_y"] < 6:
            move = self.get_idle_move(available_cards, current_elixir, evaluated_threats)
            if move: return move
        
        return None
    

if __name__ == "__main__":
    pass