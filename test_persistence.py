import sys
import os
import json

# Mock tkinter + submodules so settings_manager can import in headless environments.
from unittest.mock import MagicMock
for _mod in ("tkinter", "tkinter.messagebox", "tkinter.simpledialog",
             "tkinter.ttk", "tkinter.filedialog"):
    sys.modules.setdefault(_mod, MagicMock())

# Add the program_files directory to sys.path so we can import settings_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
program_files_dir = os.path.normpath(os.path.join(current_dir, "program_files"))
if program_files_dir not in sys.path:
    sys.path.append(program_files_dir)

try:
    import settings_manager as sm
    print("SUCCESS: settings_manager imported successfully.")

    # Test 1: Initial Load
    initial = sm.load_settings()
    print(f"Initial Settings (should have 'stats'): {initial}")
    assert "stats" in initial, "Error: 'stats' key missing from initial load."

    # Test 2: Save a new band via the public API
    test_band = {
        "name": "Test Band",
        "main_location": {"id": "1", "label": "Main", "path": "/tmp/main"},
        "secondary_locations": [],
        "structure": [{"name": "Folder 1", "is_project_folder": True}],
        "stats": {"sync_count": 42},
    }
    success = sm.save_band(test_band, is_new=True)
    print(f"Save Success: {success}")
    assert success is True, "Error: save_band returned False."

    # Test 3: Reload and Verify from disk (bypass in-memory cache to prove persistence)
    data_path = os.path.normpath(os.path.join(current_dir, "data", "settings.json"))
    assert os.path.exists(data_path), f"Error: settings file not on disk at {data_path}"
    with open(data_path, "r", encoding="utf-8") as f:
        on_disk = json.load(f)

    band_found = any(b.get("name") == "Test Band" for b in on_disk["bands"])
    assert band_found, "Error: Test band not found in settings.json on disk."

    disk_stats = on_disk.get("stats", {})
    print(f"On-disk stats: {disk_stats}")
    # save_band persists the whole settings dict; the band's own stats live on the band
    on_disk_band = next(b for b in on_disk["bands"] if b.get("name") == "Test Band")
    assert on_disk_band.get("stats", {}).get("sync_count") == 42, \
        f"Error: Expected sync_count 42, got {on_disk_band.get('stats', {}).get('sync_count')}"

    print("\nVERIFICATION COMPLETE: All tests passed.")
except Exception as e:
    print(f"\nVERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
