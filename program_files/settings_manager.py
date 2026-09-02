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
def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create data directory {DATA_DIR}: {e}")

_ensure_data_dir()

default_settings = {
    "bands": [],
    "theme": "light",
    "stats": {}  # Added as requested by the persistence task
}

# Global state for settings
_settings = None


def save_settings(data=None):
    """Persists the provided settings dictionary (or the current global state) to the JSON file.

    Returns True on success, False on failure.
    """
    global _settings
    if data is not None:
        _settings = data

    try:
        _ensure_data_dir()
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
    """Saves a new band or updates an existing one, then persists to disk.

    Returns True if the band was persisted successfully.
    """
    if _settings is None:
        load_settings()

    if is_new:
        # Verify necessary keys are present for a new band object
        for key in ("main_location", "secondary_locations", "structure"):
            if key not in band:
                band[key] = []
        if "stats" not in band:
            band["stats"] = {}
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
    if _settings is None:
        load_settings()
    return _settings.get("bands", [])


def update_stats(key, value):
    """Updates a specific statistic and persists it."""
    if _settings is None:
        load_settings()
    if "stats" not in _settings:
        _settings["stats"] = {}
    _settings["stats"][key] = value
    return save_settings()


def _drive_info_for(path):
    """Best-effort drive metadata via location_manager.

    location_manager uses Windows-only calls (ctypes.windll), so on non-Windows
    platforms this degrades gracefully to a derived id/label instead of raising.
    """
    try:
        import location_manager as lm
        return lm.get_drive_info(path)
    except Exception:
        label = os.path.basename(os.path.normpath(path)) or "Local Disk"
        return {"id": os.path.normpath(path).replace(os.sep, "_"), "label": label, "path": path}


def _default_root():
    """Return the active Tk root window, falling back to the default root if present."""
    try:
        return tk._default_root
    except Exception:
        return None


def open_band_editor(band, is_new, root=None):
    """Opens the band create/edit dialog.

    The inner Save handler collects the form values into `band` and persists via
    save_band(), which routes through save_settings() to disk.
    """
    if root is None:
        root = _default_root()
    if root is None:
        raise RuntimeError("open_band_editor requires a Tk root window.")

    win = tk.Toplevel(root)
    win.transient(root)
    win.grab_set()
    win.title("Edit Band" if not is_new else "Create Band")
    win.geometry("400x700")

    # --- BAND NAME ---
    tk.Label(win, text="Band Name:").pack()
    name_var = tk.StringVar(value=band.get("name", ""))
    name_entry = tk.Entry(win, textvariable=name_var, width=40)
    name_entry.pack(pady=5)

    # --- MAIN LOCATION ---
    tk.Label(win, text="Main Location:").pack()

    main_value = band.get("main_location", "")
    if isinstance(main_value, dict):
        main_loc_path_var = tk.StringVar(value=main_value.get("path", ""))
    else:
        main_loc_path_var = tk.StringVar(value=main_value)

    main_entry = tk.Entry(win, textvariable=main_loc_path_var, width=40)
    main_entry.pack(pady=5)

    def browse_main_location():
        path = filedialog.askdirectory()
        if path:
            info = _drive_info_for(path)
            band["main_location"] = {
                "id": f"{info['id']}",
                "label": info["label"] or "unknown",
                "path": path,
            }
            main_loc_path_var.set(band["main_location"]["path"])

    tk.Button(win, text="Browse...", command=browse_main_location).pack(pady=2)

    # --- SECONDARY LOCATIONS ---
    tk.Label(win, text="Secondary Locations:").pack(pady=5)

    sec_listbox = tk.Listbox(win, width=40, height=6)
    sec_listbox.pack()

    if "secondary_locations" not in band:
        band["secondary_locations"] = []

    for loc in band["secondary_locations"]:
        sec_listbox.insert(tk.END, f"{loc['label']} -> ({loc['path']})")

    def add_secondary():
        path = filedialog.askdirectory()
        if path:
            info = _drive_info_for(path)
            new_loc = {
                "id": f"{info['id']}",
                "label": info["label"] or "unknown",
                "path": path,
            }
            band["secondary_locations"].append(new_loc)
            sec_listbox.insert(tk.END, f"{new_loc['label']} -> ({new_loc['path']})")

    def remove_secondary():
        sel = sec_listbox.curselection()
        if sel:
            index = sel[0]
            sec_listbox.delete(index)
            band["secondary_locations"].pop(index)

    tk.Button(win, text="Add Secondary Location", command=add_secondary).pack(pady=2)
    tk.Button(win, text="Remove Selected", command=remove_secondary).pack(pady=2)

    # --- STRUCTURE LIST ---
    tk.Label(win, text="Folder Structure:").pack(pady=5)

    structure_frame = tk.Frame(win)
    structure_frame.pack()

    folder_widgets = []  # list of dicts: {name_var, check_var}

    def rebuild_structure_ui():
        for w in structure_frame.winfo_children():
            w.destroy()
        for folder in folder_widgets:
            row = tk.Frame(structure_frame)
            row.pack(fill="x", pady=2)
            name_entry = tk.Entry(row, textvariable=folder["name_var"], width=25)
            name_entry.pack(side="left", padx=2)
            check = tk.Checkbutton(row, text="Project", variable=folder["check_var"])
            check.pack(side="left", padx=5)

    def load_existing_structure():
        for f in band.get("structure", []):
            name = f["name"] if isinstance(f, dict) else f
            isproj = f.get("is_project_folder", False) if isinstance(f, dict) else False
            folder_widgets.append({
                "name_var": tk.StringVar(value=name),
                "check_var": tk.BooleanVar(value=isproj),
            })
        rebuild_structure_ui()

    load_existing_structure()

    def add_folder():
        folder_widgets.append({
            "name_var": tk.StringVar(value="New Folder"),
            "check_var": tk.BooleanVar(value=False),
        })
        rebuild_structure_ui()

    def remove_folder():
        if folder_widgets:
            folder_widgets.pop()
            rebuild_structure_ui()

    tk.Button(win, text="Add Folder", command=add_folder).pack(pady=2)
    tk.Button(win, text="Remove Folder", command=remove_folder).pack(pady=2)

    # --- SAVE BUTTON ---
    def on_save_clicked(*args):
        band["name"] = name_var.get().strip()
        if isinstance(band.get("main_location"), dict):
            band["main_location"]["path"] = main_loc_path_var.get()
        band["structure"] = [
            {
                "name": f["name_var"].get(),
                "is_project_folder": f["check_var"].get(),
            }
            for f in folder_widgets
        ]

        # Route through the persistence layer so the change actually hits disk.
        ok = save_band(band, is_new)
        if ok is False:
            messagebox.showerror("Save failed", "Could not save settings to disk.")
            return
        win.destroy()

    tk.Button(win, text="Save", command=on_save_clicked).pack(pady=15)


# Initialization - MUST be at the bottom after all function definitions
_settings = load_settings()
