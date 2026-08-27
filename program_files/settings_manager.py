import os
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog

# Define paths robustly relative to this script's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(BASE_DIR, ".."))
DATA_DIR = os.path.normpath(os.path.join(PROJECT_ROOT, "data"))
SETTINGS_FILE = os.path.normpath(os.path.join(DATA_DIR, "settings.json"))

# Ensure the data directory exists
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create data directory {DATA_DIR}: {e}")

default_settings = {
    "bands": [],
    "theme": "light",
    "stats": {}  # Added as requested by the persistence task
}

# Global state for settings
_settings = None

def save_settings(data=None):
    """Persists the provided settings dictionary (or the current global state) to the JSON file."""
    global _settings
    if data is not None:
        _settings = data
    
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_settings, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving settings to {SETTINGS_FILE}: {e}")
        return False

def load_settings():
    """Loads settings from the JSON file or creates a default one if it doesn't exist."""
    global _settings
    if _settings is not None:
        return _settings
    
    if not os.path.exists(SETTINGS_FILE):
        _settings = default_settings.copy()
        save_settings(_settings)
        return _settings
    
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure mandatory keys exist in the loaded data
            if "stats" not in data:
                data["stats"] = {}
            if "bands" not in data:
                data["bands"] = []
            _settings = data
            return _settings
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Error loading settings file: {e}")
        _settings = default_settings.copy()
        return _settings

def save_band(band, is_new):
    """Saves a new band or updates an existing one in the global settings."""
    if is_new:
        # Verify necessary keys are present for a new band object
        required = ["name", "main_location", "secondary_locations", "structure", "stats"]
        for key in required:
            if key not in band:
                band[key] = {} if key == "stats" else []

        _settings["bands"].append(band)
    else:
        # Find the band by name and update it. If multiple exist, update the first one found.
        for i, b in enumerate(_settings["bands"]):
            if b.get("name") == band.get("name"):
                _settings["bands"][i] = band
                break
    
    return save_settings()

def get_all_bands():
    """Returns the list of all bands."""
    return _settings.get("bands", [])

def update_stats(key, value):
    """Updates a specific statistic and persists it."""
    if "stats" not in _settings:
        _settings["stats"] = {}
    _settings["stats"][key] = value
    return save_settings()

# Initialization - MUST be at the bottom after all function definitions
_settings = load_settings()
