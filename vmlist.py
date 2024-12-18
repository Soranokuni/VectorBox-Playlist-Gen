#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, messagebox, Menu, simpledialog
from tkinter import ttk
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from tkinter.font import Font
import datetime
import threading  # Import the threading module

# Global variables
directory_path = ""
default_load_dir = ""
default_save_dir = ""
typed_str = []  # For alphanumeric search

def extract_bxx_info(bxx_file_path):
    try:
        with open(bxx_file_path, "r", encoding="utf-8") as file:
            bxx_content = file.read()
        tree = ET.ElementTree(ET.fromstring(bxx_content))
        root = tree.getroot()

        # Find the VideoStream with the largest Duration
        video_streams = root.findall("VideoStream")
        max_duration = 0
        video_standards = []  # List to store video standards
        for stream in video_streams:
            try:
                file_trim_in = int(stream.find("VideoStreamElement/FileTrimIn").text)
                file_trim_out = int(stream.find("VideoStreamElement/FileTrimOut").text)
                duration = file_trim_out - file_trim_in
            except:
                duration = int(stream.find("Duration").text)
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

# --- Function to load directory ---
def load_directory():
    global directory_path
    directory_path = default_load_dir   # Use filedialog to select directory
    if directory_path:
        try:
            files = [
                f
                for f in os.listdir(directory_path)
                if f.endswith((".bxx", ".BXX"))
            ]
            
            # Sort files while ignoring case
            files.sort(key=str.lower)  

            listbox_left.delete(0, tk.END)
            for file in files:
                listbox_left.insert(tk.END, file)
            listbox_left.focus_set()
            update_total_duration_display()
        except FileNotFoundError:
            messagebox.showerror(
                "Error", f"Directory not found: {directory_path}"
            )
            directory_path = ""
    update_total_duration_display() 

# --- Function to add file to the right listbox ---
def add_file(event=None):
    try:
        selected_index = listbox_left.curselection()[0]
    except IndexError:
        selected_index = listbox_left.index(tk.ANCHOR)
    file = listbox_left.get(selected_index)
    listbox_right.insert(tk.END, file)
    listbox_left.delete(selected_index)

    update_total_duration_display()  # Add this line

# --- Function to remove file from the right listbox ---
def remove_file(event=None):
    try:
        selected_index = listbox_right.curselection()[0]
    except IndexError:
        return
    file = listbox_right.get(selected_index)
    listbox_left.insert(tk.END, file)
    listbox_right.delete(selected_index)

    update_total_duration_display()

# --- Function to clear the right listbox ---
def clear_right_list():
    listbox_right.delete(0, tk.END)

# --- Function to move items between listboxes with spacebar ---
def move_item_spacebar(event=None):
    try:
        if listbox_left.curselection():
            add_file()
            listbox_left.focus_set()
            listbox_left.selection_set(listbox_left.curselection()[0] if listbox_left.curselection() else "")
            listbox_left.activate(listbox_left.curselection()[0] if listbox_left.curselection() else "")
        elif listbox_right.curselection():
            remove_file()
            listbox_left.focus_set()
            listbox_left.selection_set(listbox_left.size() - 1)
            listbox_left.activate(listbox_left.size() - 1)
    except (tk.TclError, IndexError):
        pass


# --- Functions that allow to edit the right list order ---
def move_item_up(event=None):
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
# /--- Functions that allow to edit the right list order ---/


# --- Function to move all items to the left listbox ---
def move_all_items(source_listbox, target_listbox):
    for i in range(source_listbox.size()):
        item = source_listbox.get(i)
        target_listbox.insert(tk.END, item)
    source_listbox.delete(0, tk.END)

def save_playlist(event=None):
    global directory_path, root
    if not directory_path or listbox_right.size() == 0:
        messagebox.showwarning(
            "Warning", "Please load a directory and add files to the playlist."
        )
        return

    # Get list title from the entry box
    list_title = list_title_entry.get()

    # Ask for the 4-digit input
    four_digits = simpledialog.askstring("Input", "Enter 4 digits:", parent=root)
    if (
        four_digits is None
        or len(four_digits) != 4
        or not four_digits.isdigit()
    ):
        messagebox.showerror("Error", "Invalid input. Please enter 4 digits.")
        return

    # Construct the default filename
    default_filename = f"{list_title}_{four_digits}.plx"

    # Construct the full save path
    playlist_path = os.path.join(default_save_dir, default_filename)

    playlist = ET.Element("PlayList")

    # Calculate ListDuration (sum durations of individual .bxx files in frames)
    total_duration_frames = 0
    fps = 25  # Assuming 25fps for this application

    for index in range(listbox_right.size()):
        file_name = listbox_right.get(index)
        bxx_file_path = os.path.join(directory_path, file_name)

        # Extract .bxx info
        bxx_info = extract_bxx_info(bxx_file_path)
        if bxx_info:
            total_duration_frames += bxx_info["duration"]

    # Convert total duration from frames to hh:mm:ss:ff
    def format_duration(duration_frames, fps=25):
        total_seconds = duration_frames // fps
        frames = duration_frames % fps
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

    list_duration_str = format_duration(total_duration_frames, fps=fps)

    # Static meta-information with calculated ListDuration
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
        element = ET.SubElement(playlist, tag)
        element.text = text

    # Storage Units (static for now)
    storage_units = ET.SubElement(playlist, "StorageUnits")
    ET.SubElement(storage_units, "UnitPath").text = "Y:"
    ET.SubElement(storage_units, "UnitPath").text = "D:"

    # Add selected files as <Item> in the playlist
    for index in range(listbox_right.size()):
        file_name = listbox_right.get(index)
        bxx_file_path = os.path.join(directory_path, file_name)
        bxx_info = extract_bxx_info(bxx_file_path)

        if bxx_info:
            item = ET.SubElement(playlist, "Item")
            ET.SubElement(item, "VBUniqueId").text = str(1732565760 + index * 7)  # Unique ID adjustment
            ET.SubElement(item, "Type").text = "DISK"
            ET.SubElement(item, "ItemIndex").text = str(index + 1)

            # Add file details to the <Title> element
            title = ET.SubElement(item, "Title")
            ET.SubElement(title, "TitleId").text = os.path.splitext(file_name)[0]
            ET.SubElement(title, "FilePath").text = bxx_file_path
            ET.SubElement(title, "Caption").text = os.path.splitext(file_name)[0]
            ET.SubElement(title, "Duration").text = str(bxx_info["duration"])

            # Add clip details
            clip_data = ET.SubElement(title, "ClipData")
            ET.SubElement(clip_data, "Duration").text = str(bxx_info["duration"])
            
            # Add VideoStandard elements
            for video_standard in bxx_info["video_standards"]:
                ET.SubElement(clip_data, "VideoStandard").text = video_standard

            # Add metadata
            meta_data = ET.SubElement(item, "MetaData")
            ET.SubElement(meta_data, "MxfTCData", DropFrame="0").text = "0"
            ET.SubElement(meta_data, "Generator").text = "v3-executor"

            # Static server ID
            ET.SubElement(item, "ServerID").text = "0"

    # Convert, format, and save the XML
    xml_str = ET.tostring(playlist, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml_str = parsed_xml.toprettyxml(indent="  ")

    try:
        with open(playlist_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml_str)
        messagebox.showinfo("Success", f"Playlist saved as {playlist_path}")
        load_directory()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save playlist: {e}")



# --- Function to handle keyboard events for browsing the left listbox ---
def on_left_listbox_keypress(event):
    global search_timer
    key = event.char.lower()
    if key.isalnum():
        typed_str.append(key)

        if search_timer is not None:
            search_timer.cancel()

        search_timer = threading.Timer(1.0, reset_search)
        search_timer.start()

        search_str = "".join(typed_str)
        match_found = False

        # First, try exact matching from the beginning
        for i in range(listbox_left.size()):
            item = listbox_left.get(i).lower()
            if item.startswith(search_str):
                listbox_left.selection_clear(0, tk.END)
                listbox_left.selection_set(i)
                listbox_left.activate(i)
                listbox_left.see(i)
                match_found = True
                break

        # If no exact match, try partial matching
        if not match_found:
            for i in range(listbox_left.size()):
                item = listbox_left.get(i).lower()
                if search_str in item:
                    listbox_left.selection_clear(0, tk.END)
                    listbox_left.selection_set(i)
                    listbox_left.activate(i)
                    listbox_left.see(i)
                    break
def reset_search():
    global typed_str
    typed_str.clear()

# Initialize search_timer
search_timer = None

# --- Menu Functions ---
def set_load_directory():
    global default_load_dir
    default_load_dir = filedialog.askdirectory()
    save_settings()

def set_save_directory():
    global default_save_dir
    default_save_dir = filedialog.askdirectory()
    save_settings()

def save_settings():
    with open("config.txt", "w") as f:
        f.write(f"load_dir:{default_load_dir}\n")
        f.write(f"save_dir:{default_save_dir}\n")

def load_settings():
    global default_load_dir, default_save_dir
    try:
        with open("config.txt", "r") as f:
            for line in f:
                try:
                    key, value = line.strip().split(":", 1)
                    if key == "load_dir":
                        default_load_dir = value
                    elif key == "save_dir":
                        default_save_dir = value
                except ValueError:
                    print(f"Warning: Invalid line in config.txt: {line.strip()}")
                    continue
    except FileNotFoundError:
        default_load_dir = ""
        default_save_dir = ""

        # --- Function to move items between listboxes with spacebar ---
def move_item_spacebar(event=None):
    try:
        if listbox_left.curselection():
            add_file()
            listbox_left.focus_set()
            listbox_left.selection_set(
                listbox_left.curselection()[0]
                if listbox_left.curselection()
                else ""
            )
            listbox_left.activate(
                listbox_left.curselection()[0]
                if listbox_left.curselection()
                else ""
            )
        elif listbox_right.curselection():
            remove_file()
            listbox_left.focus_set()
            listbox_left.selection_set(listbox_left.size() - 1)
            listbox_left.activate(listbox_left.size() - 1)
    except (tk.TclError, IndexError):
        pass

# --- Function to move all items to the left listbox ---
def move_all_items(source_listbox, target_listbox):
    for i in range(source_listbox.size()):
        item = source_listbox.get(i)
        target_listbox.insert(tk.END, item)
    source_listbox.delete(0, tk.END)
    update_total_duration_display()

# --- Function to update duration display ---
def update_duration_display():
    try:
        selected_index = listbox_left.curselection()[0]
        file_name = listbox_left.get(selected_index)
        bxx_file_path = os.path.join(directory_path, file_name)
        bxx_info = extract_bxx_info(bxx_file_path)
        if bxx_info:
            duration_ms = int(bxx_info["duration"]) 
            duration_str = format_duration(duration_ms)
            duration_label.config(text=duration_str)
    except (IndexError, AttributeError):
        duration_label.config(text="")

# --- Function to update total duration display ---
def update_total_duration_display():
    total_duration_frames = 0
    fps = 25  # Assuming 25fps for this application

    for i in range(listbox_right.size()):
        file_name = listbox_right.get(i)
        bxx_file_path = os.path.join(directory_path, file_name)

        # Extract .bxx info
        bxx_info = extract_bxx_info(bxx_file_path)
        if bxx_info:
            total_duration_frames += bxx_info["duration"]

    # Convert total duration from frames to hh:mm:ss:ff
    def format_duration(duration_frames, fps=25):
        total_seconds = duration_frames // fps
        frames = duration_frames % fps
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

    total_duration_str = format_duration(total_duration_frames, fps=fps)
    total_duration_label.config(text=total_duration_str)


# --- Function to format duration in hh:mm:ss:ms ---
def format_duration(duration_frames, fps=25):
    total_seconds = duration_frames // fps
    frames = duration_frames % fps
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"





def duplicate_entry(event=None):
    try:
        selected_index = listbox_right.curselection()[0]
        item = listbox_right.get(selected_index)
        listbox_right.insert(tk.END, item)  # Add the duplicated item to the end
        update_total_duration_display()
    except IndexError:
        pass  # Do nothing if no item is selected

def handle_listbox_select(event):
    listbox = event.widget
    selection = listbox.curselection()
    for i in range(listbox.size()):
        if i in selection:
            listbox.itemconfig(i, bg=nord_muted_yellow, fg=nord_fg, font=Font(family="Intel One Mono", size=911, weight="bold"))  # Use muted yellow for highlight
        else:
            listbox.itemconfig(i, bg=nord_bg, fg=nord_green if listbox == listbox_left else nord_pink, font=Font(family="Intel One Mono", size=11))
# --- Theme Functions ---
def apply_theme(theme_name):
    global nord_bg, nord_fg, nord_green, nord_yellow, nord_blue, nord_pink

    if theme_name == "Nord Aurora":
        # Apply Nord Aurora color scheme
        nord_bg = "#2e3440"
        nord_fg = "#eceff4"
        nord_green = "#a3be8c"
        nord_yellow = "#ebcb8b"
        nord_blue = "#81a1c1"
        nord_pink = "#bf616a"
    elif theme_name == "Monokai Light":
        # Apply Monokai Light color scheme
        nord_bg = "#f9f9f9"
        nord_fg = "#272822"
        nord_green = "#75715e"
        nord_yellow = "#f18f4d"
        nord_pink = "#f92672"
        nord_blue = "#66d9ef"
    elif theme_name == "Monokai Dark":
        # Apply Monokai Dark color scheme
        nord_bg = "#272822"
        nord_fg = "#f8f8f2"
        nord_green = "#a6e22e"
        nord_yellow = "#fd971f"
        nord_pink = "#f92672"
        nord_blue = "#66d9ef"
    elif theme_name == "Dracula":
        # Apply Dracula color scheme
        nord_bg = "#282a36"
        nord_fg = "#f8f8f2"
        nord_green = "#50fa7b"
        nord_yellow = "#f1fa8c"
        nord_pink = "#ff79c6"
        nord_blue = "#bd93f9"
    elif theme_name == "Solarized Light":
        # Apply Solarized Light color scheme
        nord_bg = "#fdf6e3"
        nord_fg = "#657b83"
        nord_green = "#859900"
        nord_yellow = "#b58900"
        nord_pink = "#dc322f"
        nord_blue = "#268bd2"

    update_theme()

def update_theme():
    style.configure("TFrame", background=nord_bg)
    style.configure("TButton", background=nord_yellow, foreground=nord_fg)
    style.configure("TLabel", background=nord_bg, foreground=nord_fg)
    style.configure("TListbox", background=nord_bg, foreground=nord_fg, selectbackground=nord_blue)
    root.configure(bg=nord_bg)

    # Update listbox colors
    for i in range(listbox_left.size()):
        listbox_left.itemconfig(i, bg=nord_bg, fg=nord_green)
    for i in range(listbox_right.size()):
        listbox_right.itemconfig(i, bg=nord_bg, fg=nord_pink)

    # Update duration label colors
    duration_label.config(background=nord_bg, foreground=nord_fg)
    total_duration_label.config(background=nord_bg, foreground=nord_pink)



# --- GUI Setup ---
root = tk.Tk()
root.title("BXX Playlist Creator")
root.geometry("1200x700")

# Load settings at startup
load_settings()


# Load Roboto font (ensure it's installed on your system)
font_roboto = Font(family="Intel One Mono", size=11, weight="bold")

# Apply Nord Aurora color scheme
nord_bg = "#f7f3e8"  # PaperColor Light base
nord_fg = "#343534"  # PaperColor Light text
nord_green = "#333333"  # PaperColor Light green
nord_yellow = "#f1c40f"  # PaperColor Light yellow
nord_blue = "#3498db"  # PaperColor Light blue
nord_pink = "#e74c3c"  # PaperColor Light red (for right listbox)
nord_muted_yellow = "#ffffcc"  # Muted yellow for selection highlight

# Style configuration
style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background=nord_bg)
style.configure("TButton", background=nord_yellow, foreground=nord_fg)
style.configure("TLabel", background=nord_bg, foreground=nord_fg)
style.configure("TListbox", background=nord_bg, foreground=nord_fg, selectbackground=nord_blue)

# Left frame for listing .bxx files
frame_left = ttk.Frame(root)
frame_left.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

# Create the left listbox here, before calling load_directory()
listbox_left = tk.Listbox(
    frame_left,
    selectmode=tk.SINGLE,
    width=30,
    height=30,
    bg=nord_bg,
    fg=nord_green,
    font=Font(family="Roboto", size=9,weight="bold"),
    exportselection=False,
    highlightthickness=3,
    highlightbackground=nord_blue,
)
listbox_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
listbox_left.bind("<Key>", on_left_listbox_keypress)
listbox_left.bind("<<ListboxSelect>>", handle_listbox_select)  # Bind selection event

# Add a scrollbar to the left listbox
scrollbar_left = ttk.Scrollbar(frame_left, orient="vertical")
scrollbar_left.pack(side=tk.RIGHT, fill=tk.Y)

# Configure the listbox and scrollbar to work together
listbox_left.config(yscrollcommand=scrollbar_left.set)
scrollbar_left.config(command=listbox_left.yview)

btn_load = ttk.Button(frame_left, text="Load Directory", command=load_directory)
btn_load.pack(side=tk.BOTTOM, pady=5)

# Right frame for showing selected files
frame_right = ttk.Frame(root)
frame_right.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

listbox_right = tk.Listbox(
    frame_right,
    selectmode=tk.SINGLE,
    width=30,
    height=30,
    bg=nord_bg,
    fg=nord_pink,
    font=font_roboto,
    highlightthickness=1,
    highlightbackground=nord_pink,
)
listbox_right.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

# Bind Ctrl+Up and Ctrl+Down to move items
listbox_right.bind("<Control-Up>", move_item_up)
listbox_right.bind("<Control-Down>", move_item_down)

# Frame for buttons
button_frame = ttk.Frame(root)
button_frame.pack(pady=10)

# Buttons to move items between listboxes (stacked vertically)
btn_move_right = ttk.Button(button_frame, text=">", command=add_file, width=5)
btn_move_right.pack(pady=5)

btn_move_left = ttk.Button(button_frame, text="<", command=remove_file, width=5)
btn_move_left.pack(pady=5)

btn_move_all_left = ttk.Button(button_frame, text="<<", command=lambda: move_all_items(listbox_right, listbox_left), width=5)
btn_move_all_left.pack(pady=5)

listbox_right.bind("<Button-3>", duplicate_entry)  # Bind right-click event


# --- Menu Bar ---
menubar = Menu(root)

filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label="Set Load Directory", command=set_load_directory)
filemenu.add_command(label="Set Save Directory", command=set_save_directory)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)

thememenu = Menu(menubar, tearoff=0)  # Create the Theme menu
thememenu.add_command(label="Nord Aurora", command=lambda: apply_theme("Nord Aurora"))
thememenu.add_command(label="Monokai Light", command=lambda: apply_theme("Monokai Light"))
thememenu.add_command(label="Monokai Dark", command=lambda: apply_theme("Monokai Dark"))
thememenu.add_command(label="Dracula", command=lambda: apply_theme("Dracula"))
thememenu.add_command(label="Solarized Light", command=lambda: apply_theme("Solarized Light"))
menubar.add_cascade(label="Theme", menu=thememenu)  # Add the Theme menu

root.config(menu=menubar)

# Text box for list title
current_date = datetime.datetime.now().strftime("%d-%m")
list_title_entry = ttk.Entry(root, width=50)
list_title_entry.insert(0, current_date)  
list_title_entry.pack(pady=10)

# Frame for buttons
button_frame = ttk.Frame(root)
button_frame.pack()

# Buttons to move items between listboxes (stacked vertically)
btn_move_right = ttk.Button(button_frame, text=">", command=add_file, width=5)
btn_move_right.pack(pady=5)

btn_move_left = ttk.Button(button_frame, text="<", command=remove_file, width=5)
btn_move_left.pack(pady=5)

btn_move_all_left = ttk.Button(button_frame, text="<<", command=lambda: move_all_items(listbox_right, listbox_left), width=5)
btn_move_all_left.pack(pady=5)

# Save button
btn_save = ttk.Button(button_frame, text="Save Playlist", command=save_playlist)
btn_save.pack(pady=5)


# Duration display for the left listbox
duration_label = ttk.Label(
    button_frame,  # Place in the button_frame
    text="",
    background=nord_bg,
    foreground=nord_fg,
    font=Font(family="Roboto", size=10, weight="bold"),
    borderwidth=2,
    relief="solid",
)
duration_label.pack(side=tk.LEFT, anchor="w", padx=10, pady=5)
listbox_left.bind("<<ListboxSelect>>", lambda event: update_duration_display())
 
# Total duration display for the right listbox
total_duration_label = ttk.Label(
    button_frame,  # Place in the button_frame
    text="",
    background=nord_bg,
    foreground=nord_pink,
    font=Font(family="Roboto", size=10, weight="bold"),
    borderwidth=2,
    relief="solid",
)
total_duration_label.pack(side=tk.RIGHT, anchor="e", padx=10, pady=5)
listbox_right.bind("<<ListboxSelect>>", lambda event: update_total_duration_display())
listbox_right.bind("<KeyRelease>", lambda event: update_total_duration_display())
listbox_right.bind("<ButtonRelease-1>", lambda event: update_total_duration_display())  # Add this line

root.bind('<space>', lambda event: move_item_spacebar(event))
root.bind('<Control-S>', save_playlist)  # Case-insensitive Ctrl+S binding
root.bind('<Control-s>', save_playlist)
# Apply overall window background color
root.configure(bg=nord_bg)

# Load directory at startup (after listbox_left is defined)
if default_load_dir:
    load_directory()

root.mainloop()