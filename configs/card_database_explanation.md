# 📖 Bot Database: JSON Formatting Guide

The `card_database.json` file uses a deeply nested structure to organize complex card statistics. This guide explains how to traverse the dictionary trees when writing bot logic.

## 1. Top-Level Hierarchy
The JSON is split into three main dictionaries:
* `threat_priorities`: A flat `{"String": Integer}` map. Used to rank targets.
* `counters`: A nested map linking enemy names to optimal defense arrays (`primary`, `secondary`, `spell`).
* `cards`: The core database containing deeply nested stats for every card in our deck.

## 2. Parsing the `cards` Dictionary
Every card is its own dictionary containing both **static** attributes (which never change) and **scaling** attributes (which change based on card level).

### Static Attributes
These are stored as direct key-value pairs at the root of the card object.
* `class`: Int (`0` = Spell, `1` = Troop, `2` = Champion)
* `elixir`: Int
* `range`: Float (Attack range in tiles)
* `placement_offset`: Float (Distance in tiles to place away from target)

### Scaling Attributes (The "Level" Nesting)
Stats like `health`, `damage`, and `crown_tower_damage` are **not** integers. They are nested dictionaries mapping a Level (String) to a Stat (Integer).
* **Why Strings?** JSON requires dictionary keys to be strings.
* **How to parse in Python:** To get a Level 11 PEKKA's damage, your code must extract it like this:
  `database["cards"]["PEKKA"]["damage"]["11"]`

## 3. The `ability` Sub-Dictionary
If a card has special mechanics (dashes, spawn damage, piercing), it contains an `ability` dictionary. 

* **Static Ability Stats:** Mechanics like `stun_duration` or `charge_range` are stored as flat values or lists.
* **Scaling Ability Stats:** If the ability deals damage (like the Bandit's dash or Electro Wizard's spawn zap), it will contain *another* nested `damage` dictionary.
* **How to parse in Python:**
  To get a Level 14 Bandit's Dash Damage:
  `database["cards"]["Bandit"]["ability"]["damage"]["14"]`

### ⚠️ Developer Best Practices
1. **Always use `.get()` in Python:** When querying levels or abilities, use `.get("14", default_value)` to prevent `KeyError` crashes if the bot encounters an unknown level.
2. **Remember your Types:** Always cast your level variables to `str()` before querying the JSON, otherwise the lookup will fail!