import sys
from unittest.mock import MagicMock

# Mocking tkinter before importing settings_manager
sys.modules["tkinter"] = MagicMock()
sys.modules["tkinter.messagebox"] = MagicMock()
sys.modules["tkinter.simpledialog"] = MagicMock()
sys.modules["tkinter.ttk"] = MagicMock()
sys.modules["tkinter.filedialog"] = MagicMock()

# Add the program_files directory to sys.path
program_files_dir = "/opt/data/git_projects/Artist-Synch/.worktrees/t_e9122e38/program_files"
if program_files_dir not in sys.path:
    sys.path.append(program_files_dir)

try:
    import settings_manager as sm
    print("Successfully imported settings_manager")
except Exception as e:
    print(f"Failed to import settings_manager: {e}")
    sys.exit(1)

# Test initial load/creation
print(f"Initial bands count: {len(sm.get_all_bands())}")

# Test saving a new band
test_band = {
    "name": "Verification Band",
    "main_location": "Loc1",
    "secondary_locations": ["Loc2"],
    "structure": "S1",
    "stats": {"v": 1}
}
success = sm.save_band(test_band, is_new=True)
print(f"Save new band success: {success}")

# Verify it exists in memory and on disk
bands = sm.get_all_bands()
print(f"Bands after save: {len(bands)}")
if len(bands) > 0 and bands[0]["name"] == "Verification Band":
    print("Verification successful: Verification Band found in memory.")

# Check file on disk
actual_path = "/opt/data/git_projects/Artist-Synch/.worktrees/t_e9122e38/data/settings.json"
import os
if os.path.exists(actual_path):
    with open(actual_path, "r") as f:
        content = f.read()
        print(f"File content on disk:\n{content}")
else:
    print("Error: settings.json not found on disk.")

# Test updating a band
test_band["stats"]["v"] = 2
success_update = sm.save_band(test_band, is_new=False)
print(f"Update band success: {success_update}")
print(f"Updated count in memory: {sm.get_all_bands()[0]['stats']['v']}")

# Test stats update function
sm.update_stats("last_used", "2026-08-24")
if sm._settings.get("stats", {}).get("last_used") == "2026-08-24":
    print("Update stats success: Correct value found in settings.")
else:
    print(f"Update stats failed. Current stats: {sm._settings.get('stats')}")
