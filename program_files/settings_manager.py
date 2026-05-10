import json

import os
import tkinter as tk

import location_manager as lm
import location_manager as lm
from tkinter.messagebox import askyesno
from tkinter.simpledialog import askstring
from tkinter.simpledialog import Dialog
from tkinter import scrolledtext
from tkinter.messagebox import askyesno
from tkinter import filedialog
from tkinter import ttk
from tkinter import simpledialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "../data/settings.json")

default_settings = {
    "bands": [],
    "theme": "light"
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(default_settings)
        return default_settings

    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        # If the file is corrupted, recreate it
        save_settings(default_settings)
        return default_settings

settings = load_settings()

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def open_band_editor(band, is_new):
    win = tk.Toplevel(root)
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
        # Display only the path of the main location
        main_loc_path_var = tk.StringVar(value=main_value.get("path", ""))
    else:
        # If it's already a string or empty, show it as-is
        main_loc_path_var = tk.StringVar(value=main_value)

    main_entry = tk.Entry(win, textvariable=main_loc_path_var, width=40)
    main_entry.pack(pady=5)

    def browse_main_location():
        path = filedialog.askdirectory()
        if path:
            info = lm.get_drive_info(path)

            band["main_location"] = {
                "id": f"{info['id']}",
                "label": info["label"] or "unknown",
                "path": path
            }
           
            main_loc_path_var.set(band["main_location"]["path"])

    tk.Button(win, text="Browse...", command=browse_main_location).pack(pady=2)

    # --- SECONDARY LOCATIONS ---
    tk.Label(win, text="Secondary Locations:").pack(pady=5)

    sec_listbox = tk.Listbox(win, width=40, height=6)
    sec_listbox.pack()

    # Ensure key exists
    if "secondary_locations" not in band:
        band["secondary_locations"] = []

    for loc in band["secondary_locations"]:
        #print(loc)
        sec_listbox.insert(tk.END, f"{loc['label']}  ({loc['path']})")

    def add_secondary():
        path = filedialog.askdirectory()
        if path:
            info = lm.get_drive_info(path)

            new_loc = {
                "id": f"{info['id']}",
                "label": info["label"] or "unknown",
                "path": path
            }
            print(new_loc)

            band["secondary_locations"].append(new_loc)

            # Show pretty label instead of full JSON
            sec_listbox.insert(tk.END, f"{new_loc['label']}  ({new_loc['path']})")

    def remove_secondary():
        sel = sec_listbox.curselection()
        if sel:
            sec_listbox.delete(sel)

    tk.Button(win, text="Add Secondary Location", command=add_secondary).pack(pady=2)
    tk.Button(win, text="Remove Selected", command=remove_secondary).pack(pady=2)

    # --- STRUCTURE LIST ---
    tk.Label(win, text="Folder Structure:").pack(pady=5)

    structure_frame = tk.Frame(win)
    structure_frame.pack()

    folder_widgets = []  # list of dicts: {frame, name_var, check_var}

    def rebuild_structure_ui():
        # Clear UI
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
                "check_var": tk.BooleanVar(value=isproj)
            })

        rebuild_structure_ui()

    load_existing_structure()

    # Buttons: Add / Remove folder
    def add_folder():
        folder_widgets.append({
            "name_var": tk.StringVar(value="New Folder"),
            "check_var": tk.BooleanVar(value=False)
        })
        rebuild_structure_ui()

    def remove_folder():
        if folder_widgets:
            folder_widgets.pop()  # remove last; could add selection UI later
            rebuild_structure_ui()

    tk.Button(win, text="Add Folder", command=add_folder).pack(pady=2)
    tk.Button(win, text="Remove Folder", command=remove_folder).pack(pady=2)

    # --- SAVE BUTTON ---
    def save_band():
        band["name"] = name_var.get().strip()


        if isinstance(band.get("main_location"), dict):
            band["main_location"]["path"] = main_loc_path_var.get()


        band["structure"] = [
            {
                "name": f["name_var"].get(),
                "is_project_folder": f["check_var"].get()
            }
            for f in folder_widgets
        ]
        #band["secondary_locations"] = list(sec_listbox.get(0, tk.END))

        if is_new:
            settings["bands"].append(band)

        save_settings(settings)
        
        win.destroy()

    tk.Button(win, text="Save", command=save_band).pack(pady=15)