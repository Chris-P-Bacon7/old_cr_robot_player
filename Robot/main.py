import cv2
import numpy as np
import keyboard
import time
import json
import os
import threading
import queue
import random as rand
import ctypes
from concurrent.futures import ThreadPoolExecutor
from perception.window_capture import WindowCapture
from automation.game_controller import GameController
from perception.card_vision import CardVision
from perception.elixir_tracker import ElixirTracker
from perception.arena_vision import ArenaVision
from automation.placement_optimization import PlayAutomation
from perception.screen_mapper import ScreenMapper
from automation.game_state import GameState
from tools.json_worker import JsonWorker
from automation.play_strategy import PlayStrategy

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

# ================= CONFIGURATION =================
arena_width = 18
arena_height = 30
phones = {
    "riley": "SM-A536W",
    "chris": "SM-S936W"
    }
decks = {
    "riley": ["Fireball", "Bats", "SkeletonArmy", "Valkyrie", "Tesla", 
              "Musketeer_Hero", "Log", "HogRider"],
    "chris": ["Fireball", "PEKKA", "Bandit", "BattleRam",
              "RoyalGhost", "Zap", "MagicArcher", "ElectroWizard"]
}

json_name = "Chris_S25.json"
json_location = f"robot\\{json_name}"
db_json_name = "card_database.json"
json_worker = JsonWorker(json_location, json_name)

def typewriter(text):
        length = len(text)
  
        for i in range(length):
            print(text[i], end="", flush=True)
            try:
                if text[i + 1] in [",", ".", "?", "!"]:
                    time.sleep(rand.uniform(0.3, 0.65))
                else:
                    time.sleep(rand.uniform(0.04, 0.065))
            except IndexError:
                time.sleep(rand.uniform(0.04, 0.065))
            
        return ""

def time_calibration(time_data):
    initial_time = time_data[0][0]
    initial_match = time_data[0][1]
    i = 1
    
    while time_data[i][1] == initial_match:
        i += 1
    
    return time_data[i][0] - initial_time     

def get_slot_from_name(card_name, raw_hand, screen_config):
    # Find the card's vision data in hand
    target_card = None
    for card in raw_hand:
        if card[0] == card_name:
            target_card = card
            break
 
    if not target_card:
        return None # Report card not found in hand
    
    card_x = target_card[1][0]
    best_slot = None
    min_dist = 9999

    for i in range(1, 5):
        slot_key = f"card_{i}"
        if slot_key in screen_config:
            slot_x, _ = screen_config[slot_key]
            dist = abs(card_x - slot_x)
            if dist < min_dist:
                min_dist = dist
                best_slot = str(i)
    
    return best_slot

def arena_ai_thread(detector, input_queue, output_queue):
    while True:
        try:
            frame = input_queue.get(timeout=0.1)
            
            # Removes redundant items in the queue
            while not input_queue.empty():
                try:
                    frame = input_queue.get_nowait() 
                except queue.Empty:
                    pass

            results = list(detector.find_troops(frame, 0.700))

            if not output_queue.empty():
                try: output_queue.get_nowait()
                except queue.Empty: pass
            
            output_queue.put(results)
    
        except queue.Empty:
            continue # Loop again if no frame received
        except Exception as e:
            print(f"AI Thread Error: {e}")

def card_vision_thread(card_vision, deck_list, input_queue, output_queue):
    while True:
        try:
            frame = input_queue.get(timeout=0.1)
            h_frame, w_frame = frame.shape[:2]
            roi_top = int(h_frame * 0.85)
            hand_view = frame[roi_top:h_frame, 0:w_frame]

            raw_hand = []
            for card_name in deck_list:
                matches = card_vision.find(hand_view, card_name, threshold=0.700)

                for ((x, y, w, h), score) in matches:
                    real_y = y + roi_top
                    raw_hand.append((card_name, (x, real_y, w, h), score))   
            
            if not output_queue.empty():
                try: output_queue.get_nowait()
                except queue.Empty: pass
            output_queue.put(raw_hand)
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Card Thread Error: {e}")

def score_vision_thread(score_tracker, input_queue, output_queue):
    while True:
        try:
            frame = input_queue.get(timeout=0.1)

            while not input_queue.empty():
                try: frame = input_queue.get_nowait()
                except queue.Empty: pass
            
            tower_state = score_tracker.tower_state(frame)
            health_data = tower_state[0]

            if not output_queue.empty():
                try: output_queue.get_nowait()
                except queue.Empty: pass
            output_queue.put(health_data)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Score Thread Error: {e}")

def action_thread(slot, loc):
    bot_state["is_acting"] = True
    try:
        time.sleep(rand.uniform(0.05, 0.1))
        bot_controls.play_card(f"card_{slot}", loc, screen_config, screen_mapper)
    except Exception as e:
        print(f"Action Failed: {e}.")
    bot_state["is_acting"] = False

# ================= MAIN LOOP ====================
if __name__ == "__main__":
    # --- INITIALIZE USER ---
    while True:
        # user = input(typewriter("Enter your name: ")).lower()
        user = "chris"
        if user in phones:
            window_name = phones[user]
            deck = decks[user]
            time.sleep(0.5)
            typewriter(f"Welcome, {user.capitalize()}!\n")
            time.sleep(0.75)
            break
        elif user == "":
            print("Oops...looks like you accidentally entered nothing!")
            time.sleep(1.5)
        else:
            typewriter(f"{user.title()}?\n")
            time.sleep(1.5)
            typewriter("What kind of name is that?\n")
            time.sleep(1.5)
            typewriter("Get the hell off of my program >:(\n\n")
            time.sleep(1.5)
            print(f"CRITICAL ERROR DETECTED -> Please see traceback:\n"
                  f"UserError: The program has terminated due to an ineligible user \"{user.title()}\".")
            exit()
    
    # --- INITIALIZE EVERYTHING ELSE ---
    screen_config = json_worker.config_json_coord(json_location, json_name)
    raw_json = json_worker.load_json(json_location, json_name)

    # Initialize all classes
    cap = WindowCapture(window_name, json_location)
    screen_mapper = ScreenMapper(screen_config, arena_height, arena_width)
    bot_controls = GameController(cap)
    card_vision = CardVision()
    elixir_tracker = ElixirTracker(screen_config)
    bot_logic = PlayAutomation(decks[user])
    score_tracker = GameState(json_name, json_location, db_json_name, 
                              f"robot\\{db_json_name}", screen_mapper)
    play_strategy = PlayStrategy(tuple(raw_json["match_time"]) 
                                 if raw_json and "match_time" in raw_json else ())

    arena_detector = ArenaVision("runs\\detect\\train7\\weights\\best.pt")
    names_map = arena_detector.model.names

    # Create Queues
    ai_input_queue = queue.Queue(maxsize=1)
    ai_output_queue = queue.Queue(maxsize=1) # 1 ensures the newest frame is processed only

    score_output_queue = queue.Queue(maxsize=1)
    score_input_queue = queue.Queue(maxsize=1)
    
    # Initialize Threads
    ai_thread = threading.Thread(
        target=arena_ai_thread,
        args=(arena_detector, ai_input_queue, ai_output_queue),
        daemon=True
    )
    ai_thread.start()
    print("AI Background Thread Started.")

    card_input_queue = queue.Queue(maxsize=1)
    card_output_queue = queue.Queue(maxsize=1)

    card_thread = threading.Thread(target=card_vision_thread,
                                    args=(card_vision, deck, card_input_queue, card_output_queue),
                                    daemon=True)
    card_thread.start()
    raw_hand = []
    print("Card Vision Thread Started.")

    score_thread = threading.Thread(
        target=score_vision_thread,
        args=(score_tracker, score_input_queue, score_output_queue),
        daemon=True
    )
    score_thread.start()
    print("Score Thread Started.")

    # Initialize Config
    card_keys = ["1", "2", "3", "4"]
    pos_map = {}
    pos_keys = []

    last_save_time = 0
    save_cooldown = 0.5

    if raw_json is not None and "location" in raw_json:
        for name, data in raw_json["location"].items():
            if len(data) >= 3:
                tile_x, tile_y, trigger_key = data
                pos_map[trigger_key] = (tile_x, tile_y)
                pos_keys.append(trigger_key)
    
    selected_card = None
    bot_state = {"is_acting": False}

    cards_path = "assets\\cards\\full_colour"
    num_cards = 0
    for card in deck:
        card_vision.load_template(card, cards_path, 0)
        num_cards += 1
        
        evo_path = os.path.join(cards_path, f"Card_{card}_Evo.png")
        hero_path = os.path.join(cards_path, f"Card_{card}_Hero.png")

        template_mode = 0
        if os.path.exists(evo_path):
            card_vision.load_template(card, cards_path, 1)
            num_cards += 1

        if os.path.exists(hero_path):
            card_vision.load_template(card, cards_path, 2)
            num_cards += 1

    # Initialize Window
    cv2.namedWindow("Bot Vision", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Bot Vision", 400, 848)
    cv2.setWindowProperty("Bot Vision", cv2.WND_PROP_TOPMOST, 1) # Pushes window to front but prevents it
    cv2.setWindowProperty("Bot Vision", cv2.WND_PROP_TOPMOST, 0) # from staying on top

    # <--- CACHE STATIC GRID LINES (Pre-calculate to save CPU) --->
    grid_lines = []
    text_labels = []
    
    # Vertical Lines
    for x in range(arena_width):
        center_x = x + 0.5
        p1 = screen_mapper.tile_to_pixel(center_x, 0)
        p2 = screen_mapper.tile_to_pixel(center_x, arena_height)
        grid_lines.append(p1)
        grid_lines.append(p2)
        
        # Bottom numbers
        if x % 2 == 0:
            px, py = screen_mapper.tile_to_pixel(center_x, arena_height)
            text_labels.append((str(x), (px - 6, py - 8)))

    # Horizontal Lines
    for y in range(arena_height):
        center_y = y + 0.5
        p1 = screen_mapper.tile_to_pixel(0, center_y)
        p2 = screen_mapper.tile_to_pixel(arena_width, center_y)
        grid_lines.append(p1)
        grid_lines.append(p2)
        
        # Side numbers
        if y % 2 == 0:
            px, py = screen_mapper.tile_to_pixel(0, center_y)
            text_labels.append((str(y), (px + 5, py + 5)))

    # --- LOOPED ELEMENTS BEGIN HERE ---
    with ThreadPoolExecutor(max_workers=num_cards) as executor:
        failure_count = 0
        frame_count = 0
        current_elixir = 0
        arena_results = [] # Persist results between frames
        persistent_hand = {}
        current_scores = {}
        time_calibrated = False
        both_times = []
        
        # --- INITIALIZE WINDOW POSITIONS ---
        cv2.namedWindow("Bot Vision")
        cv2.moveWindow("Bot Vision", 10, 10)  # Top-left corner
        
        # cv2.namedWindow("Match Evaluation")
        # cv2.moveWindow("Match Evaluation", 10, 800)  # Bottom-left (Adjust 800 up/down based on your screen height)
        
        while True:
            loop_start = time.time()
            frame_count += 1
            
            # --- BOT VISION WINDOW ---
            try:
                frame = cap.get_screenshot()
                if frame is None: continue
                
                clean_frame = frame.copy()
            except Exception as e:
                print(f"ERROR: Your Window: \"{window_name}\" is not open. Trying again.\n")

                failure_count += 1
                if failure_count > 30:
                    print(f"ERROR: Your session timed out because \"{window_name}\" took too long to open.")
                    break
                time.sleep(1)
                continue

            # --- CARD DETECTION ---
            if not card_input_queue.full() and frame_count % 5 == 0:
                card_input_queue.put(frame)

            try:
                raw_hand = card_output_queue.get_nowait()
            except queue.Empty:
                raw_hand = []
            
            # 1. Update persistent memory with any new cards seen
            current_time = time.time()
            for (card_name, (x, y, w, h), score) in raw_hand:
                persistent_hand[card_name] = {
                    "rect": (x, y, w, h),
                    "score": score,
                    "last_seen": current_time
                }
            
            current_hand = []
            cards_to_remove = []

            # 2. If a card isn't seen in 2 seconds, it is removed from persistent hand
            for card_name in persistent_hand:
                if current_time - persistent_hand[card_name]["last_seen"] > 1.0:
                    cards_to_remove.append(card_name)
                else:
                    current_hand.append((card_name, persistent_hand[card_name]["rect"], 
                                         persistent_hand[card_name]["score"]))

            # 3. Draw the detections
            for (card_name, (x, y, w, h), score) in current_hand:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{card_name} {score * 100:.1f}%", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # --- ELIXIR TRACKING ---
            if frame_count % 5 == 0 or frame_count == 1:
                current_elixir = elixir_tracker.get_elixir(frame)
            
            # --- MATCH STATE ---
            if not time_calibrated: 
                match_time = play_strategy.get_match_time(frame)
            else:
                try:
                    match_time = time.time() - time_diff
                except NameError:
                    print("Match time not calibrated yet.")
            both_times.append((time.time(), match_time))
            
            if len(both_times) == 100: 
                time_diff = time_calibration(both_times)
                time_calibrated = True
            
            # --- ARENA DETECTION ---
            # 1. Send current frame to the AI (Non-blocking)
            if frame_count % 5 == 0 and not ai_input_queue.full():
                ai_input_queue.put(frame.copy())

            #2. Check for new results
            try:
                new_results = ai_output_queue.get_nowait()
                arena_results = new_results
            except queue.Empty:
                pass # If no new update, keep old boxes
            
            # Draw the arena results to keep the boxes on the screen
            arena_detector.draw_detections(frame, arena_results)
            
            # --- BOT LOGIC ---
            if not bot_state["is_acting"]: 
                
                # Safely extract boxes if they exist, otherwise pass an empty list
                detections = arena_results[0].boxes if len(arena_results) > 0 else []
                
                # Ask the brain to make a move
                move = bot_logic.get_best_move(detections, current_hand, current_elixir, names_map)

                if move:
                    target_name, (target_x, target_y), enemy_data = move
                    
                    # Convert pixels back to tiles for the action clicker
                    tile_x, tile_y = screen_mapper.pixel_to_tile(target_x, target_y)

                    # Find which slot contains the card
                    slot_num = get_slot_from_name(target_name, current_hand, screen_config)

                    if slot_num:
                        action_reason = enemy_data['Troop']
                        
                        # Clean up the console logs based on Offense vs Defense
                        if "Offensive Push" in action_reason or "Cycle" in action_reason:
                            print(f"🕐 IDLE MOVE: Playing {target_name} (Slot {slot_num}) at Tile ({tile_x:.1f}, {tile_y:.1f}) -> {action_reason}")
                        else:
                            enemy_x, enemy_y = screen_mapper.pixel_to_tile(enemy_data['x'], enemy_data['y'])
                            print(f"🛡️ DEFENDING: Playing {target_name} (Slot {slot_num}) at Tile ({tile_x:.1f}, {tile_y:.1f}) "
                                  f"to counter {action_reason} at ({enemy_x:.1f}, {enemy_y:.1f}) "
                                    f"→ Evaluation (Threat Score: {move[2]['threat_score']:.1f}, ETA: {move[2]['eta']:.1f}).")
                        
                        bot_logic.commit_play(target_name, tile_x, tile_y)
                        threading.Thread(target=action_thread, args=(slot_num, (tile_x, tile_y))).start()
                    else:
                        print(f"LOGIC ERROR: Brain wanted to play {target_name}, but couldn't find the slot in hand.")

            # --- DRAWING ON BOT VISION ---
            
            # Drawing Current Elixir
            cv2.putText(frame, f"Elixir: {current_elixir}", (10, 800),
                        cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1, (210, 60, 210), 2, cv2.LINE_4)
            
            # Drawing Match Time
            cv2.putText(frame, f"Match Time: {match_time}", (10, 1000), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)

            # Draw Cached Grid Lines (Faster than calculating every frame)
            # We iterate by 2s since we stored p1, p2 sequentially
            for i in range(0, len(grid_lines), 2):
                cv2.line(frame, grid_lines[i], grid_lines[i+1], (255, 255, 255), 1, cv2.LINE_AA)

            # Draw Cached Numbers
            for text, loc in text_labels:
                cv2.putText(frame, text, loc, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(frame, text, loc, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

            # Draw Card Slots
            for i in range(1, 5):
                key_str = str(i)
                if f"card_{i}" in screen_config:
                    cx, cy = screen_config[f"card_{i}"]
                    colour = (0, 255, 255) 
                    thickness = 2
                    if selected_card == key_str:
                        colour = (0, 255, 0)
                        thickness = -1 
                    cv2.circle(frame, (cx, cy), 10, colour, thickness)
            
            fps = int(1 / (time.time() - loop_start + 0.001))
            cv2.putText(frame, f"FPS: {fps}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if bot_state["is_acting"]:
                cv2.putText(frame, "BUSY", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("Bot Vision", frame)
            
            # --- PROGRAM TERMINATION ---
            try:
                if cv2.waitKey(1) == ord('q'): break
            except KeyboardInterrupt:
                break

    print("Program successfully terminated.")
    cv2.destroyAllWindows()