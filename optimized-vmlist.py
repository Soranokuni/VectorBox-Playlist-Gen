#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, messagebox, Menu, simpledialog
from tkinter import ttk
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from tkinter.font import Font
import datetime
import threading

# --- Constants and Configuration ---
CONFIG_FILE = "config.txt"
DEFAULT_FPS = 25

# --- Global Variables ---
directory_path = ""
default_load_dir = ""
default_save_dir = ""
typed_str = []  # For alphanumeric search
search_timer = None

# --- Theme Variables (Initialized later) ---
nord_bg = ""
nord_fg = ""
nord_green = ""
nord_yellow = ""
nord_blue = ""
nord_pink = ""
nord_muted_yellow = ""

# --- Utility Functions ---
def format_duration(duration_frames, fps=DEFAULT_FPS):
    """Formats duration from frames to hh:mm:ss:ff."""
    total_seconds = duration_frames // fps
    frames = duration_frames % fps
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

# --- XML Parsing and Playlist Generation ---
def extract_bxx_info(bxx_file_path):
    """Extracts duration and video standards from a .bxx file."""
    try:
        with open(bxx_file_path, "r", encoding="utf-8") as file:
            root = ET.fromstring(file.read())

        # Find the VideoStream with the largest Duration
        video_streams = root.findall("VideoStream")
        max_duration = 0
        video_standards = []
        for stream in video_streams:
            try:
                file_trim_in = int(stream.find("VideoStreamElement/FileTrimIn").text)
                file_trim_out = int(stream.find("VideoStreamElement/FileTrimOut").text)
                duration = file_trim_out - file_trim_in
            except (AttributeError, ValueError, TypeError):
                duration_element = stream.find("Duration")
                if duration_element is not None:
                    duration = int(duration_element.text)
                else:
                    duration = 0

            if duration > max_duration:
                max_duration = duration

            # Extract VideoStandard
            video_standard_element = stream.find("VideoStandard")
            if video_standard_element is not None:
                video_standards.append(video_standard_element.text)

        return {
            "duration": max_duration,
            "video_standards": video_standards,
        }
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse {bxx_file_path}: {e}")
        return None

def save_playlist(event=None):
    """Saves the current playlist to a .plx file."""
    global directory_path
    if not directory_path or listbox_right.size() == 0:
        messagebox.showwarning(
            "Warning", "Please load a directory and add files to the playlist."
        )
        return

    list_title = list_title_entry.get()
    four_digits = simpledialog.askstring("Input", "Enter 4 digits:", parent=root)
    if (
        four_digits is None
        or len(four_digits) != 4
        or not four_digits.isdigit()
    ):
        messagebox.showerror("Error", "Invalid input. Please enter 4 digits.")
        return

    default_filename = f"{list_title}_{four_digits}.plx"
    playlist_path = os.path.join(default_save_dir, default_filename)

    playlist = ET.Element("PlayList")
    total_duration_frames = 0

    for index in range(listbox_right.size()):
        file_name = listbox_right.get(index)
        bxx_file_path = os.path.join(directory_path, file_name)
        bxx_info = extract_bxx_info(bxx_file_path)
        if bxx_info:
            total_duration_frames += bxx_info["duration"]

    list_duration_str = format_duration(total_duration_frames)

    meta_info = {
        "DayModified": "2460640",
        "TimeModified": "80231904",
        "ListDuration": list_duration_str,
        "TimeScale": "25fps",
        "ExportedBy": "Vector3",
        "ApplicationName": "V-BOX MCR",
        "ApplicationRelease": "4.09.r207",
        "ApplicationBuild": "28",
        "CatalogueDir": "\\Catalogue",
    }

    for tag, text in meta_info.items():
        ET.SubElement(playlist, tag).text = text

    storage_units = ET.SubElement(playlist, "StorageUnits")
    ET.SubElement(storage_units, "UnitPath").text = "Y:"
    ET.SubElement(storage_units, "UnitPath").text = "D:"

    for index in range(listbox_right.size()):
        file_name = listbox_right.get(index)
        bxx_file_path = os.path.join(directory_path, file_name)
        bxx_info = extract_bxx_info(bxx_file_path)

        if bxx_info:
            item = ET.SubElement(playlist, "Item")
            ET.SubElement(item, "VBUniqueId").text = str(1732565760 + index * 7)
            ET.SubElement(item, "Type").text = "DISK"
            ET.SubElement(item, "ItemIndex").text = str(index + 1)

            title = ET.SubElement(item, "Title")
            ET.SubElement(title, "TitleId").text = os.path.splitext(file_name)[0]
            ET.SubElement(title, "FilePath").text = bxx_file_path
            ET.SubElement(title, "Caption").text = os.path.splitext(file_name)[0]
            ET.SubElement(title, "Duration").text = str(bxx_info["duration"])

            clip_data = ET.SubElement(title, "ClipData")
            ET.SubElement(clip_data, "Duration").text = str(bxx_info["duration"])

            for video_standard in bxx_info["video_standards"]:
                ET.SubElement(clip_data, "VideoStandard").text = video_standard

            meta_data = ET.SubElement(item, "MetaData")
            ET.SubElement(meta_data, "MxfTCData", DropFrame="0").text = "0"
            ET.SubElement(meta_data, "Generator").text = "v3-executor"

            ET.SubElement(item, "ServerID").text = "0"

    xml_str = ET.tostring(playlist, encoding="utf-8")
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")

    try:
        with open(playlist_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml_str)
        messagebox.showinfo("Success", f"Playlist saved as {playlist_path}")
        load_directory()  # Refresh the left listbox
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save playlist: {e}")

# --- Listbox Management ---
def load_directory():
    """Loads .bxx files from the selected directory into the left listbox."""
    global directory_path
    directory_path = default_load_dir
    if directory_path:
        try:
            files = sorted(
                [
                    f
                    for f in os.listdir(directory_path)
                    if f.lower().endswith((".bxx"))
                ],
                key=str.lower
            )
            listbox_left.delete(0, tk.END)
            for file in files:
                listbox_left.insert(tk.END, file)
            listbox_left.focus_set()
        except FileNotFoundError:
            messagebox.showerror(
                "Error", f"Directory not found: {directory_path}"
            )
            directory_path = ""
        finally:
            update_total_duration_display()

def add_file(event=None):
    """Adds the selected file from the left listbox to the right listbox."""
    try:
        selected_index = listbox_left.curselection()[0]
        file = listbox_left.get(selected_index)
        listbox_right.insert(tk.END, file)
        listbox_left.delete(selected_index)
        update_total_duration_display()
    except IndexError:
        pass

def remove_file(event=None):
    """Removes the selected file from the right listbox and returns it to the left."""
    try:
        selected_index = listbox_right.curselection()[0]
        file = listbox_right.get(selected_index)
        listbox_left.insert(tk.END, file)
        listbox_right.delete(selected_index)
        update_total_duration_display()
    except IndexError:
        pass

def clear_right_list():
    """Clears all items from the right listbox."""
    listbox_right.delete(0, tk.END)
    update_total_duration_display()

def move_item_up(event=None):
    """Moves the selected item up in the right listbox."""
    try:
        selection = listbox_right.curselection()
        if not selection:
            return
        index = selection[0]
        if index > 0:
            item = listbox_right.get(index)
            listbox_right.delete(index)
            listbox_right.insert(index - 1, item)
            listbox_right.selection_set(index - 1)
            update_total_duration_display()
    except IndexError:
        pass

def move_item_down(event=None):
    """Moves the selected item down in the right listbox."""
    try:
        selection = listbox_right.curselection()
        if not selection:
            return
        index = selection[0]
        if index < listbox_right.size() - 1:
            item = listbox_right.get(index)
            listbox_right.delete(index)
            listbox_right.insert(index + 1, item)
            listbox_right.selection_set(index + 1)
            update_total_duration_display()
    except IndexError:
        pass

def move_all_items(source_listbox, target_listbox):
    """Moves all items from the source listbox to the target listbox."""
    for i in range(source_listbox.size()):
        target_listbox.insert(tk.END, source_listbox.get(i))
    source_listbox.delete(0, tk.END)
    update_total_duration_display()

def duplicate_entry(event=None):
    """Duplicates the selected entry in the right listbox."""
    try:
        selected_index = listbox_right.curselection()[0]
        listbox_right.insert(tk.END, listbox_right.get(selected_index))
        update_total_duration_display()
    except IndexError:
        pass

# --- Search and Navigation ---
def on_left_listbox_keypress(event):
    """Handles keyboard events for alphanumeric search in the left listbox."""
    global search_timer
    key = event.char.lower()
    if key.isalnum():
        typed_str.append(key)

        if search_timer is not None:
            search_timer.cancel()

        search_timer = threading.Timer(1.0, reset_search)
        search_timer.start()

        search_str = "".join(typed_str)

        # Prioritize exact matches from the beginning
        for i in range(listbox_left.size()):
            if listbox_left.get(i).lower().startswith(search_str):
                listbox_left.selection_clear(0, tk.END)
                listbox_left.selection_set(i)
                listbox_left.activate(i)
                listbox_left.see(i)
                return  # Exit after finding an exact match

        # If no exact match, try partial matching
        for i in range(listbox_left.size()):
            if search_str in listbox_left.get(i).lower():
                listbox_left.selection_clear(0, tk.END)
                listbox_left.selection_set(i)
                listbox_left.activate(i)
                listbox_left.see(i)
                break

def reset_search():
    """Resets the alphanumeric search string."""
    global typed_str
    typed_str.clear()

def move_item_spacebar(event=None):
    """Moves the selected item between listboxes using the spacebar."""
    try:
        if listbox_left.curselection():
            add_file()
            listbox_left.selection_set(listbox_left.curselection()[0])
            listbox_left.activate(listbox_left.curselection()[0])
        elif listbox_right.curselection():
            remove_file()
            listbox_left.selection_set(listbox_left.size() - 1)
            listbox_left.activate(listbox_left.size() - 1)
        listbox_left.focus_set()
    except (tk.TclError, IndexError):
        pass

# --- Duration Display ---
def update_duration_display():
    """Updates the duration display for the selected item in the left listbox."""
    try:
        selected_index = listbox_left.curselection()[0]
        file_name = listbox_left.get(selected_index)
        bxx_file_path = os.path.join(directory_path, file_name)
        bxx_info = extract_bxx_info(bxx_file_path)
        if bxx_info:
            duration_label.config(text=format_duration(bxx_info["duration"]))
        else:
            duration_label.config(text="")
    except (IndexError, AttributeError, TypeError):
        duration_label.config(text="")

def update_total_duration_display():
    """Updates the total duration display for the right listbox."""
    total_duration_frames = sum(
        extract_bxx_info(os.path.join(directory_path, listbox_right.get(i)))["duration"]
        for i in range(listbox_right.size())
        if extract_bxx_info(os.path.join(directory_path, listbox_right.get(i)))
    )
    total_duration_label.config(text=format_duration(total_duration_frames))

# --- Configuration and Settings ---
def save_settings():
    """Saves the current settings (load/save directories) to config.txt."""
    with open(CONFIG_FILE, "w") as f:
        f.write(f"load_dir:{default_load_dir}\n")
        f.write(f"save_dir:{default_save_dir}\n")

def load_settings():
    """Loads settings from config.txt."""
    global default_load_dir, default_save_dir
    try:
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                key, value = line.strip().split(":", 1)
                if key == "load_dir":
                    default_load_dir = value
                elif key == "save_dir":
                    default_save_dir = value
    except (FileNotFoundError, ValueError):
        default_load_dir = ""
        default_save_dir = ""

def set_load_directory():
    """Sets the default load directory."""
    global default_load_dir
    default_load_dir = filedialog.askdirectory()
    save_settings()

def set_save_directory():
    """Sets the default save directory."""
    global default_save_dir
    default_save_dir = filedialog.askdirectory()
    save_settings()

# --- Theme Management ---
def apply_theme(theme_name):
    """Applies the selected color theme."""
    global nord_bg, nord_fg, nord_green, nord_yellow, nord_blue, nord_pink, nord_muted_yellow

    if theme_name == "Nord Aurora":
        nord_bg = "#2e3440"
        nord_fg = "#eceff4"
        nord_green = "#a3be8c"
        nord_yellow = "#ebcb8b"
        nord_blue = "#81a1c1"
        nord_pink = "#bf616a"
    elif theme_name == "Monokai Light":
        nord_bg = "#f9f9f9"
        nord_fg = "#272822"
        nord_green = "#75715e"
        nord_yellow = "#f18f4d"
        nord_pink = "#f92672"
        nord_blue = "#66d9ef"
    elif theme_name == "Monokai Dark":
        nord_bg = "#272822"
        nord_fg = "#f8f8f2"
        nord_green = "#a6e22e"
        nord_yellow = "#fd971f"
        nord_pink = "#f92672"
        nord_blue = "#66d9ef"
    elif theme_name == "Dracula":
        nord_bg = "#282a36"
        nord_fg = "#f8f8f2"
        nord_green = "#50fa7b"
        nord_yellow = "#f1fa8c"
        nord_pink = "#ff79c6"
        nord_blue = "#bd93f9"
    elif theme_name == "Solarized Light":
        nord_bg = "#fdf6e3"
        nord_fg = "#657b83"
        nord_green = "#859900"
        nord_yellow = "#b58900"
        nord_pink = "#dc322f"
        nord_blue = "#268bd2"
    
    nord_muted_yellow = "#ffffcc" 

    update_theme()

def update_theme():
    """Updates the GUI elements with the current theme colors."""
    style.configure("TFrame", background=nord_bg)
    style.configure("TButton", background=nord_yellow, foreground=nord_fg, font=font_roboto)
    style.configure("TLabel", background=nord_bg, foreground=nord_fg, font=font_roboto)
    style.configure("TListbox", background=nord_bg, foreground=nord_fg, selectbackground=nord_blue, font=font_roboto, highlightthickness=1, highlightbackground=nord_blue)
    root.configure(bg=nord_bg)

    # Configure listboxes *after* they are created
    if 'listbox_left' in globals():  # Check if listbox_left has been defined
        listbox_left.configure(selectbackground=nord_muted_yellow, highlightbackground=nord_blue)
        for i in range(listbox_left.size()):
            listbox_left.itemconfig(i, bg=nord_bg, fg=nord_green)

    if 'listbox_right' in globals():  # Check if listbox_right has been defined
        listbox_right.configure(selectbackground=nord_muted_yellow, highlightbackground=nord_pink)
        for i in range(listbox_right.size()):
            listbox_right.itemconfig(i, bg=nord_bg, fg=nord_pink)

    duration_label.config(background=nord_bg, foreground=nord_fg)
    total_duration_label.config(background=nord_bg, foreground=nord_pink)

# --- GUI Setup and Event Handling ---
def handle_listbox_select(event):
    """Handles listbox selection events, highlighting the selected item."""
    listbox = event.widget
    selection = listbox.curselection()
    for i in range(listbox.size()):
        if i in selection:
            listbox.itemconfig(i, bg=nord_muted_yellow, fg=nord_fg, font=font_roboto)
        else:
            listbox.itemconfig(
                i,
                bg=nord_bg,
                fg=nord_green if listbox == listbox_left else nord_pink,
                font=font_roboto,
            )

root = tk.Tk()
root.title("BXX Playlist Creator")
root.geometry("1200x700")

# --- Style ---
# Create the style object *before* applying the theme
style = ttk.Style()
style.theme_use("clam")

# Load settings 
load_settings()

# Define font_roboto *after* creating the root window
font_roboto = Font(family="Intel One Mono", size=11, weight="bold")

# --- Frames ---
frame_left = ttk.Frame(root)
frame_left.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

frame_right = ttk.Frame(root)
frame_right.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

button_frame = ttk.Frame(root)
button_frame.pack(pady=10)

# --- Listboxes ---
# Create listboxes *before* applying the theme
listbox_left = tk.Listbox(frame_left, selectmode=tk.SINGLE, exportselection=False)
listbox_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
listbox_left.bind("<Key>", on_left_listbox_keypress)
listbox_left.bind("<<ListboxSelect>>", handle_listbox_select)
listbox_left.bind("<<ListboxSelect>>", lambda event: update_duration_display())

scrollbar_left = ttk.Scrollbar(frame_left, orient="vertical", command=listbox_left.yview)
scrollbar_left.pack(side=tk.RIGHT, fill=tk.Y)
listbox_left.config(yscrollcommand=scrollbar_left.set)

listbox_right = tk.Listbox(frame_right, selectmode=tk.SINGLE)
listbox_right.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
listbox_right.bind("<Control-Up>", move_item_up)
listbox_right.bind("<Control-Down>", move_item_down)
listbox_right.bind("<Button-3>", duplicate_entry)
listbox_right.bind("<<ListboxSelect>>", handle_listbox_select)
listbox_right.bind("<<ListboxSelect>>", lambda event: update_total_duration_display())
listbox_right.bind("<KeyRelease>", lambda event: update_total_duration_display())
listbox_right.bind("<ButtonRelease-1>", lambda event: update_total_duration_display())

# --- Labels and Entry ---
# Create labels *before* applying the theme
current_date = datetime.datetime.now().strftime("%d-%m")
list_title_entry = ttk.Entry(root, width=50)
list_title_entry.insert(0, current_date)
list_title_entry.pack(pady=10)

duration_label = ttk.Label(button_frame, text="")
duration_label.pack(side=tk.LEFT, anchor="w", padx=10, pady=5)

total_duration_label = ttk.Label(button_frame, text="")
total_duration_label.pack(side=tk.RIGHT, anchor="e", padx=10, pady=5)

# Now apply the theme
apply_theme("Nord Aurora")  # Default theme

# --- Buttons ---
btn_load = ttk.Button(frame_left, text="Load Directory", command=load_directory)
btn_load.pack(side=tk.BOTTOM, pady=5)

btn_move_right = ttk.Button(button_frame, text=">", command=add_file, width=5)
btn_move_right.pack(pady=5)

btn_move_left = ttk.Button(button_frame, text="<", command=remove_file, width=5)
btn_move_left.pack(pady=5)

btn_move_all_left = ttk.Button(
    button_frame,
    text="<<",
    command=lambda: move_all_items(listbox_right, listbox_left),
    width=5,
)
btn_move_all_left.pack(pady=5)

btn_save = ttk.Button(button_frame, text="Save Playlist", command=save_playlist)
btn_save.pack(pady=5)

# --- Menu Bar ---
menubar = Menu(root)
root.config(menu=menubar)

filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label="Set Load Directory", command=set_load_directory)
filemenu.add_command(label="Set Save Directory", command=set_save_directory)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)

thememenu = Menu(menubar, tearoff=0)
thememenu.add_command(label="Nord Aurora", command=lambda: apply_theme("Nord Aurora"))
thememenu.add_command(
    label="Monokai Light", command=lambda: apply_theme("Monokai Light")
)
thememenu.add_command(
    label="Monokai Dark", command=lambda: apply_theme("Monokai Dark")
)
thememenu.add_command(label="Dracula", command=lambda: apply_theme("Dracula"))
thememenu.add_command(
    label="Solarized Light", command=lambda: apply_theme("Solarized Light")
)
menubar.add_cascade(label="Theme", menu=thememenu)

# --- Keyboard Shortcuts ---
root.bind("<space>", lambda event: move_item_spacebar(event))
root.bind("<Control-s>", save_playlist)
root.bind("<Control-S>", save_playlist)

# --- Initialization ---
if default_load_dir:
    load_directory()

root.mainloop()