#!/usr/bin/env python3

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
from tkinter.font import Font
import datetime
import threading

# Global Variables
directory_path = ""
default_load_dir = ""
default_save_dir = ""
typed_str = []
search_timer = None

# --- Helper Functions ---
def format_duration(duration_frames, fps=25):
    """Convert frame duration to hh:mm:ss:ff format."""
    total_seconds = duration_frames // fps
    frames = duration_frames % fps
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

def extract_bxx_info(bxx_file_path):
    """Extract video stream duration from a .bxx file."""
    try:
        with open(bxx_file_path, "r", encoding="utf-8") as file:
            bxx_content = file.read()
        tree = ET.ElementTree(ET.fromstring(bxx_content))
        root = tree.getroot()

        max_duration = max(
            int(stream.findtext("VideoStreamElement/FileTrimOut", 0)) -
            int(stream.findtext("VideoStreamElement/FileTrimIn", 0))
            for stream in root.findall("VideoStream")
        )
        return {"duration": max_duration}
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse {bxx_file_path}: {e}")
        return None

# --- Directory Management ---
def load_directory():
    """Load .bxx files from the directory."""
    global directory_path
    directory_path = default_load_dir or filedialog.askdirectory()
    if directory_path:
        try:
            files = sorted(
                [f for f in os.listdir(directory_path) if f.lower().endswith(".bxx")],
                key=str.lower
            )
            listbox_left.delete(0, tk.END)
            for file in files:
                listbox_left.insert(tk.END, file)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Directory not found: {directory_path}")
            directory_path = ""
    update_total_duration_display()

def save_playlist():
    """Save the playlist to an XML file."""
    if not directory_path or listbox_right.size() == 0:
        messagebox.showwarning("Warning", "Load a directory and add files first.")
        return

    list_title = list_title_entry.get()
    four_digits = simpledialog.askstring("Input", "Enter 4 digits:")
    if not (four_digits and len(four_digits) == 4 and four_digits.isdigit()):
        messagebox.showerror("Error", "Invalid input. Enter 4 digits.")
        return

    filename = f"{list_title}_{four_digits}.plx"
    playlist_path = os.path.join(default_save_dir, filename)

    playlist = ET.Element("PlayList")
    meta_info = {
        "DayModified": "2460640",
        "ListDuration": format_duration(
            sum(extract_bxx_info(os.path.join(directory_path, listbox_right.get(i)))["duration"] for i in range(listbox_right.size()) if extract_bxx_info),
            fps=25
        ),
        "ApplicationName": "V-BOX MCR",
    }
    for tag, text in meta_info.items():
        ET.SubElement(playlist, tag).text = text

    try:
        with open(playlist_path, "w", encoding="utf-8") as f:
            f.write(parseString(ET.tostring(playlist)).toprettyxml())
        messagebox.showinfo("Success", f"Playlist saved: {playlist_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save playlist: {e}")


# --- Directory Management ---
def set_load_directory():
    """Set the default directory for loading files."""
    global default_load_dir
    default_load_dir = filedialog.askdirectory()
    if default_load_dir:
        messagebox.showinfo("Info", f"Load directory set to: {default_load_dir}")
        save_settings()

def set_save_directory():
    """Set the default directory for saving files."""
    global default_save_dir
    default_save_dir = filedialog.askdirectory()
    if default_save_dir:
        messagebox.showinfo("Info", f"Save directory set to: {default_save_dir}")
        save_settings()

def save_settings():
    """Save default directories to a configuration file."""
    try:
        with open("config.txt", "w") as f:
            f.write(f"load_dir:{default_load_dir}\n")
            f.write(f"save_dir:{default_save_dir}\n")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save settings: {e}")

def load_settings():
    """Load default directories from a configuration file."""
    global default_load_dir, default_save_dir
    try:
        with open("config.txt", "r") as f:
            for line in f:
                key, value = line.strip().split(":", 1)
                if key == "load_dir":
                    default_load_dir = value
                elif key == "save_dir":
                    default_save_dir = value
    except FileNotFoundError:
        default_load_dir = ""
        default_save_dir = ""


# --- Event Handlers ---
def add_file():
    """Move selected file from left to right."""
    try:
        selected = listbox_left.curselection()[0]
        file = listbox_left.get(selected)
        listbox_right.insert(tk.END, file)
        listbox_left.delete(selected)
        update_total_duration_display()
    except IndexError:
        pass

def remove_file():
    """Move selected file from right to left."""
    try:
        selected = listbox_right.curselection()[0]
        file = listbox_right.get(selected)
        listbox_left.insert(tk.END, file)
        listbox_right.delete(selected)
        update_total_duration_display()
    except IndexError:
        pass

def on_keypress(event):
    """Handle alphanumeric search in left listbox."""
    global search_timer
    typed_str.append(event.char.lower())
    search_str = "".join(typed_str)
    if search_timer:
        search_timer.cancel()
    search_timer = threading.Timer(1.0, typed_str.clear)
    search_timer.start()
    for i in range(listbox_left.size()):
        if listbox_left.get(i).lower().startswith(search_str):
            listbox_left.selection_clear(0, tk.END)
            listbox_left.selection_set(i)
            listbox_left.activate(i)
            listbox_left.see(i)
            break

def update_total_duration_display():
    """Update total duration label for the right listbox."""
    total_frames = sum(
        extract_bxx_info(os.path.join(directory_path, listbox_right.get(i)))["duration"]
        for i in range(listbox_right.size()) if extract_bxx_info
    )
    total_duration_label.config(text=format_duration(total_frames, fps=25))

# --- GUI Setup ---
root = tk.Tk()
root.title("BXX Playlist Creator")
root.geometry("800x600")

listbox_left = tk.Listbox(root)
listbox_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
listbox_left.bind("<Key>", on_keypress)

listbox_right = tk.Listbox(root)
listbox_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

btn_save = tk.Button(root, text="Save Playlist", command=save_playlist)
btn_save.pack()

total_duration_label = tk.Label(root, text="Total Duration: 00:00:00:00")
total_duration_label.pack()

# --- Menu Bar ---
menubar = tk.Menu(root)

# File menu
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label="Set Load Directory", command=set_load_directory)
filemenu.add_command(label="Set Save Directory", command=set_save_directory)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)

root.config(menu=menubar)

load_settings()
if default_load_dir:
    load_directory()

root.mainloop()
