import tkinter as tk
import psutil
import tkinter as tk
import sys
import threading
import queue
import synchronizer
import os
import ctypes
import uuid

from tkinter.messagebox import askyesno
from tkinter.simpledialog import askstring
from tkinter.simpledialog import Dialog
from tkinter import scrolledtext
from tkinter.messagebox import askyesno
from tkinter import filedialog
from tkinter import ttk
from tkinter import simpledialog

from synchronizer import folder_synch, copy_band_projects

from settings_manager import load_settings, save_settings

class ConsoleRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, message):
        # If robocopy outputs a carriage return-based update:
        if message.startswith("\r"):
            # Delete the last line
            self.widget.delete("end-2l", "end-1l")
            # Insert the text AFTER removing the leading "\r"
            self.widget.insert("end", message[1:])
        else:
            # Normal output
            self.widget.insert("end", message)

        self.widget.see("end")   # Auto scroll

    def flush(self):
        pass


chosen_band = None
current_band_label = None

current_origin_label = None
current_destination_label = None

origin = None
destination = None

selected_operation = None

selected_structure = []

settings = load_settings()

user_prompt_queue = queue.Queue()
user_response_queue = queue.Queue()

def gui_prompt(question, choices):
    user_prompt_queue.put((question, choices))

def gui_wait_input():
    return user_response_queue.get()   # blocks worker thread without freezing GUI


def list_mounted_drives():
    drives = []
    for part in psutil.disk_partitions(all=True):
        drives.append(part.device)  
    return drives

def location_is_mounted(loc):
    if not isinstance(loc, dict):
        return False

    loc_id = loc.get("id")
    loc_label = loc.get("label")
    loc_path = loc.get("path")

    if not loc_id or not loc_label or not loc_path:
        return False

    # Normalize stored path → extract drive root ("D:\\")
    loc_drive_root = os.path.splitdrive(loc_path)[0] + "\\"
    
    for m in mounted_drives:
        if not isinstance(m, dict):
            continue
            
        m_id = m.get("id")
        m_label = m.get("label")
        m_root  = m.get("path")

        # Normalize mounted path too
        if m_root:
            m_root = os.path.splitdrive(m_root)[0] + "\\"

        # Strict match of: id, label, and drive root
        if (
            m_id == loc_id and
            m_label == loc_label and
            m_root == loc_drive_root
        ):
            return True

    return False

def get_drive_info(path):
    # Extract drive root like "D:\\"
    drive = os.path.splitdrive(path)[0] + "\\"

    # --- Drive Label ---
    volume_name_buffer = ctypes.create_unicode_buffer(1024)
    fs_name_buffer = ctypes.create_unicode_buffer(1024)
    serial_number = ctypes.c_ulong()

    ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(drive),
        volume_name_buffer,
        ctypes.sizeof(volume_name_buffer),
        ctypes.byref(serial_number),
        None,
        None,
        fs_name_buffer,
        ctypes.sizeof(fs_name_buffer)
    )

    label = volume_name_buffer.value
    uuid_hex = hex(serial_number.value)[2:].upper()

    return {
        "id": uuid_hex,
        "label": label or "unknown",
        "path": drive
    }

drives_root = list_mounted_drives()

mounted_drives = []

for d in drives_root:
    try:
        info = get_drive_info(d)   # returns {"uuid","drive_root","label" }
        mounted_drives.append(info)
    except Exception as e:
        print("Could not get drive info for", d, e)

print("Mounted drives:", mounted_drives)
#options = settings["options"]
operations = ["Copy", "Sync Drives"]

root = tk.Tk()
root.title("Syncher")
root.geometry("1080x400") 

def add_band():
    band_name = simpledialog.askstring("Add Band", "Enter new band name:")
    if not band_name or not band_name.strip():
        return

    band_name = band_name.strip()

    # Create empty band object
    new_band = {
        "name": band_name,
        "main_location": [],
        "secondary_locations": [],
        "structure": []
    }

    # Open editor window in "create" mode
    open_band_editor(new_band, is_new=True)

def open_band_selector():
    sel_win = tk.Toplevel(root)
    sel_win.title("Select Band to Edit")
    sel_win.geometry("300x300")

    tk.Label(sel_win, text="Select a band to edit:", font=("Arial", 12)).pack(pady=10)

    # Listbox
    listbox = tk.Listbox(sel_win, width=30, height=10)
    listbox.pack(pady=10)

    # Fill listbox
    for band in settings["bands"]:
        listbox.insert(tk.END, band["name"])

    # --- EDIT SELECTED BAND ---
    def edit_selected():
        sel = listbox.curselection()
        if not sel:
            return
        band_name = listbox.get(sel)

        # Find the band
        for band in settings["bands"]:
            if band["name"] == band_name:
                sel_win.destroy()
                open_band_editor(band, is_new=False)
                return

    # --- DOUBLE CLICK HANDLER ---
    def on_double_click(event):
        edit_selected()

    listbox.bind("<Double-Button-1>", on_double_click)

    # Edit button
    tk.Button(sel_win, text="Edit", command=edit_selected).pack(pady=5)

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
            info = get_drive_info(path)

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
            info = get_drive_info(path)

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
        fill_bands_panel()
        fill_structure_panel()
        win.destroy()

    tk.Button(win, text="Save", command=save_band).pack(pady=15)
def make_scrollable(parent):
    canvas = tk.Canvas(parent, borderwidth=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return scroll_frame

def go_operation():
    global origin, destination, selected_operation, selected_structure

    # --- BASE VALIDATION ---
    if origin is None or destination is None:
        print("Origin or destination not selected!")
        return

    if selected_operation is None:
        print("No operation selected!")
        return

    if not selected_structure:
        print("No structure selected!")
        return

    # --- CLEAN WINDOWS PATH FIX ---
    def winpath(p):
        if not isinstance(p, str):
            return p
        return p.replace("/", "\\").rstrip("\\")   # no trailing slash

    safe_origin = winpath(origin)
    safe_destination = winpath(destination)
    safe_structure = [winpath(f) for f in selected_structure]

    # TEMP: you were forcing this operation, so I keep it here
    selected_operation = "/xo /s /R:10 /W:10 /NJH /NJS /TEE"

    print("Selected:", safe_origin, safe_destination, safe_structure)

    # --- RUN EVERYTHING IN A BACKGROUND THREAD ---
    threading.Thread(
        target=run_sync_worker,
        args=(safe_origin, safe_destination, safe_structure, selected_operation),
        daemon=True
    ).start()



def run_sync_worker(safe_origin, safe_destination, safe_structure, selected_operation):

    print("Starting synchronization...")

    for folder in safe_structure:

        print(f"Copying folder: {folder['name']}")

        src = safe_origin + "\\" + folder["name"]
        dst = safe_destination + "\\" + folder["name"]

        # Project folder: use copy_band_projects
        if folder["is_project_folder"]:
            print(f"Project folder detected: {src}")
            copy_band_projects(src, dst)              # NO thread here
        else:
            print(f"Folder Synch: {src} -> {dst} with {selected_operation}")
            folder_synch(src, dst, selected_operation) # NO thread here

    print("Operation completed.")

# --------- REAL TOP MENU BAR ---------
menubar = tk.Menu(root)

# "GO" menu
go_menu = tk.Menu(menubar, tearoff=0)
go_menu.add_command(label="Start", command=lambda: print("Start clicked"))
go_menu.add_command(label="Stop", command=lambda: print("Stop clicked"))
go_menu.add_command(label="Run", command=go_operation)
menubar.add_cascade(label="GO", menu=go_menu)

# "CONFIG" menu
config_menu = tk.Menu(menubar, tearoff=0)
config_menu.add_command(label="Add Band", command=add_band)
config_menu.add_command(label="Edit Bands", command=open_band_selector)
menubar.add_cascade(label="CONFIG", menu=config_menu)

root.config(menu=menubar)

# ============================
#  Resizable paned layout
# ============================

# Outer split (top vs bottom)
outer_panes = ttk.PanedWindow(root, orient="vertical")
outer_panes.pack(fill="both", expand=True)

# Top split (A | B | C)
top_panes = ttk.PanedWindow(outer_panes, orient="horizontal")
outer_panes.add(top_panes, weight=1)

# Bottom split (D | E)
bottom_panes = ttk.PanedWindow(outer_panes, orient="horizontal")
outer_panes.add(bottom_panes, weight=3)

# ---- Create raw frames (will hold scrollable content) ----
A_frame = tk.Frame(top_panes, bd=1, relief="solid")
B_frame = tk.Frame(top_panes, bd=1, relief="solid")
C_frame = tk.Frame(top_panes, bd=1, relief="solid")

D_frame = tk.Frame(bottom_panes, bd=1, relief="solid")
E_frame = tk.Frame(bottom_panes, bd=1, relief="solid")

# Add frames to panes
top_panes.add(A_frame, weight=1)
top_panes.add(B_frame, weight=1)
top_panes.add(C_frame, weight=1)

bottom_panes.add(D_frame, weight=1)
bottom_panes.add(E_frame, weight=3)

# Console frame
console_frame = tk.Frame(bottom_panes, bg="white")
bottom_panes.add(console_frame, weight=2)

console_text = scrolledtext.ScrolledText(console_frame, height=10, wrap="word")
console_text.pack(fill="both", expand=True)


# ---- Make scrollable inner frames ----
A_panel = make_scrollable(A_frame)
B_panel = make_scrollable(B_frame)
C_panel = make_scrollable(C_frame)
D_panel = make_scrollable(D_frame)
E_panel = make_scrollable(E_frame)



# ====================================
#  Panel fill and support functions
# ====================================
def on_band_click(band, widget):
    global chosen_band, current_band_label, current_origin_label, current_destination_label

    chosen_band = band

    # Remove old highlight safely
    if current_band_label is not None:
        if current_band_label.winfo_exists():
            current_band_label.config(bg=A_panel.cget("bg"))
        current_band_label = None

    if current_origin_label is not None:
        if current_origin_label.winfo_exists():
            current_origin_label.config(bg=A_panel.cget("bg"))
        current_origin_label = None

    if current_destination_label is not None:
        if current_destination_label.winfo_exists():
            current_destination_label.config(bg=A_panel.cget("bg"))
        current_destination_label = None

    # Highlight new selected one
    widget.config(bg="#add8e6")
    current_band_label = widget

    # Update UI
    fill_structure_panel()
    fill_origin_panel()
    fill_destination_panel()

def fill_bands_panel():
    for w in A_panel.winfo_children():
        w.destroy()

    tk.Label(A_panel, text="Bands", font=("Arial", 12, "bold")).pack(anchor="w")

    for band in settings["bands"]:
        lbl = tk.Label(A_panel, text=band["name"], anchor="w")
        lbl.pack(fill="x")

        # Make each band clickable
        # Single click = select band
        lbl.bind("<Button-1>", lambda e, b=band, w=lbl: on_band_click(b, w))

        # Double click = open band editor immediately
        lbl.bind("<Double-Button-1>", lambda e, b=band, w=lbl: (on_band_click(b, w), open_band_editor(b, False)))


def format_location(loc):
    if not isinstance(loc, dict):
        return str(loc)

    label = loc.get("label", "unknown")
    path = loc.get("path", "")
    return f"{label} -> {path}"

def select_origin(x):
    global origin

    # If the user clicked the currently selected origin → unselect it
    if origin == x:
        origin = None
    else:
        origin = x
   
    fill_origin_panel()
    fill_destination_panel()

def add_origin_label(loc):
    global origin, destination

    # Disabled if equal to destination
    if loc == destination:
        lbl = tk.Label(B_panel, text=format_location(loc), anchor="w", fg="gray")
        lbl.pack(fill="x")
        return

    # Highlight if this is the chosen origin
    bg_color = "#add8e6" if loc == origin else B_panel.cget("bg")

    lbl = tk.Label(B_panel, text=format_location(loc), anchor="w", bg=bg_color)
    lbl.pack(fill="x")

    lbl.bind("<Button-1>", lambda e, x=loc: select_origin(x))

def fill_origin_panel():
    global origin, destination

    for w in B_panel.winfo_children():
        w.destroy()

    tk.Label(B_panel, text="Origin", font=("Arial", 12, "bold")).pack(anchor="w")

    if chosen_band is None:
        tk.Label(B_panel, text="(select a band)", fg="gray").pack(anchor="w")
        return

    # MAIN LOCATION
    main_loc = chosen_band["main_location"]
    #print("Mounted drives again:", mounted_drives)
    #print("Checking main location:", main_loc)
    if location_is_mounted(main_loc):
        add_origin_label(main_loc)
    
    # SECONDARY LOCATIONS
    for loc in chosen_band.get("secondary_locations", []):
        if location_is_mounted(loc):
            add_origin_label(loc)
        
def select_destination(x):
    global destination

    # If user clicked the already selected destination → unselect it
    if destination == x:
        destination = None
    else:
        destination = x

    fill_origin_panel()
    fill_destination_panel()

def add_destination_label(loc):
    global origin, destination

    # Disabled if equal to origin
    if loc == origin:
        lbl = tk.Label(C_panel, text=format_location(loc), anchor="w", fg="gray")
        lbl.pack(fill="x")
        return

    # Highlight if this is the chosen destination
    bg_color = "#add8e6" if loc == destination else C_panel.cget("bg")

    lbl = tk.Label(C_panel, text=format_location(loc), anchor="w", bg=bg_color)
    lbl.pack(fill="x")

    lbl.bind("<Button-1>", lambda e, x=loc: select_destination(x))

def fill_destination_panel():
    global origin, destination

    for w in C_panel.winfo_children():
        w.destroy()

    tk.Label(C_panel, text="Destination", font=("Arial", 12, "bold")).pack(anchor="w")

    if chosen_band is None:
        tk.Label(C_panel, text="(select a band)", fg="gray").pack(anchor="w")
        return

    # MAIN LOCATION
    main_loc = chosen_band["main_location"]
    if location_is_mounted(main_loc):
        add_destination_label(main_loc)

    # SECONDARY LOCATIONS
    for loc in chosen_band.get("secondary_locations", []):
        if location_is_mounted(loc):
            add_destination_label(loc)

def fill_operations_panel():
    global selected_operation

    for w in D_panel.winfo_children():
        w.destroy()

    # ---- Header row (Operations left, GO button far right) ----
    header = tk.Frame(D_panel)
    header.pack(fill="x")

    # Left label
    tk.Label(header, text="Operations", font=("Arial", 12, "bold")).pack(side="left")

    # Spacer pushes the button to the right
    tk.Label(header, text="").pack(side="left", expand=True)

    # GO button on the far right
    go_button = tk.Button(
        header,
        text="GO",
        font=("Arial", 10, "bold"),
        bg="#406341",
        fg="white",
        command=go_operation
    )
    go_button.pack(side="right", padx=5, pady=2)

    for op in operations:

        bg_normal = D_panel.cget("bg")
        bg_selected = "#add8e6"

        # choose highlight depending on selection
        initial_bg = bg_selected if op == selected_operation else bg_normal

        lbl = tk.Label(D_panel, text=op, anchor="w", padx=10, bg=initial_bg)
        lbl.pack(fill="x")

        # proper frozen variables for hover
        lbl.bind("<Enter>", lambda e, l=lbl, o=op: on_operation_hover_enter(l, o))
        lbl.bind("<Leave>", lambda e, l=lbl, o=op: on_operation_hover_leave(l, o))

        # proper click binding
        lbl.bind("<Button-1>", lambda e, o=op: on_operation_click(o))

def on_operation_hover_enter(label, op):
    global selected_operation
    if op != selected_operation:
        label.config(bg="#e0e0e0")


def on_operation_hover_leave(label, op):
    global selected_operation
    bg_normal = D_panel.cget("bg")
    bg_selected = "#add8e6"
    label.config(bg=bg_selected if op == selected_operation else bg_normal)

def on_operation_click(op):
    global selected_operation

    # Toggle select/unselect
    if selected_operation == op:
        selected_operation = None
    else:
        selected_operation = op

    fill_operations_panel()   # refresh with correct highlight 

def add_structure_item(parent, item):
    global selected_structure

    name = item.get("name", "")
    is_project = item.get("is_project_folder", False)

    bg_normal = parent.cget("bg")
    bg_selected = "#add8e6"

    initial_bg = bg_selected if item in selected_structure else bg_normal

    lbl = tk.Label(parent, text=name, anchor="w", padx=10, bg=initial_bg)
    lbl.pack(fill="x")

    lbl.bind("<Enter>", lambda e, l=lbl: on_structure_hover_enter(l))
    lbl.bind("<Leave>", lambda e, l=lbl, i=item, n=bg_normal, s=bg_selected:
             on_structure_hover_leave(l, i, n, s))

    lbl.bind("<Button-1>", lambda e, i=item, l=lbl, n=bg_normal, s=bg_selected:
             on_structure_click(i, l, n, s))
def fill_structure_panel():
    global selected_structure

    for w in E_panel.winfo_children():
        w.destroy()

    # ---- Header ----
    header = tk.Frame(E_panel)
    header.pack(fill="x")

    tk.Label(header, text="Structure", font=("Arial", 12, "bold")).pack(side="left")

    # Expandable spacer
    tk.Label(header, text="").pack(side="left", expand=True)

    # --- Start with no selection ---
    selected_structure = []


    # If no band selected, stop
    if chosen_band is None:
        return

    structure = chosen_band.get("structure", [])

    # ---- List items ----
    for item in structure:
       add_structure_item(E_panel, item)

def on_structure_click(item, label_widget, bg_normal, bg_selected):
    global selected_structure

    if item in selected_structure:
        selected_structure.remove(item)
        label_widget.config(bg=bg_normal)
    else:
        selected_structure.append(item)
        label_widget.config(bg=bg_selected)


def on_structure_hover_enter(label_widget):
    label_widget.config(bg="#e0e0e0")

def on_structure_hover_leave(label_widget, item_name, bg_normal, bg_selected):
    # Restore correct background depending on selection
    if item_name in selected_structure:
        label_widget.config(bg=bg_selected)
    else:
        label_widget.config(bg=bg_normal)
# ====================================
#  End of panel fill and support functions
# ====================================

gui_prompt = None
gui_wait_input = None
synchronizer.gui_prompt = gui_prompt
synchronizer.gui_wait_input = gui_wait_input

# ============================
#  INITIAL DRAW
# ============================
sys.stdout = ConsoleRedirector(console_text)
sys.stderr = ConsoleRedirector(console_text)
fill_bands_panel()
fill_origin_panel()
fill_destination_panel()
fill_operations_panel()
fill_structure_panel()

root.mainloop()