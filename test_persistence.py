import sys
import os
import json

# Add the program_files directory to sys.path so we can import settings_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
program_files_dir = os.path.normpath(os.path.join(current_dir, "program_files"))
sys.path.append(program_files_dir)

try:
    import settings_manager as sm
    print("SUCCESS: settings_manager imported successfully.")
    
    # Test 1: Initial Load
    initial = sm.load_settings()
    print(f"Initial Settings (should have 'stats'): {initial}")
    assert "stats" in initial, "Error: 'stats' key missing from initial load."

    # Test 2: Save a new band
    test_band = {
        "name": "Test Band",
        "main_location": {"id": "1", "label": "Main", "path": "/tmp/main"},
        "secondary_locations": [],
        "structure": [{"name": "Folder 1", "is_project_folder": True}],
        "stats": {"sync_count": 42} # Test stats persistence
    }
    sm.settings["bands"].append(test_band)
    success = sm.save_settings(sm.settings)
    print(f"Save Success: {success}")
    assert success is True, "Error: save_settings returned False."

    # Test 3: Reload and Verify
    # We need to reload the settings object because sm.load_settings() returns a new dict
    reloaded = sm.load_settings()
    print(f"Reloaded Settings: {reloaded}")
    
    # Check if test band exists
    band_found = any(b["name"] == "Test Band" for b in reloaded["bands"])
    assert band_found, "Error: Test band not found in reloaded settings."
    
    # Check if stats persist
    reloaded_stats = reloaded.get("stats", {})
    print(f"Reloaded Stats: {reloaded_stats}")
    assert reloaded_stats.get("sync_count") == 42, f"Error: Expected sync_count 42, got {reloaded_stats.get('sync_count')}"

    print("\nVERIFICATION COMPLETE: All tests passed.")
except Exception as e:
    print(f"\nVERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
