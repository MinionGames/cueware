from pathlib import Path
import json
import tkinter as tk
from tkinter import messagebox

import pygame
from AudioManager import AudioManager


def _format_time(seconds: float) -> str:
	whole_seconds = max(0, int(seconds))
	minutes, remaining_seconds = divmod(whole_seconds, 60)
	return f"{minutes:02d}:{remaining_seconds:02d}"


def main() -> None:
	inspector_width = 510
	inspector_content_wrap = inspector_width - 40

	root = tk.Tk()
	root.title("Cueware - Seussical Audio Cue Manager")
	root.iconbitmap("assets/SeussHat.ico")
	root.geometry("1200x800")
	root.minsize(900, 600)
	root.configure(bg="#121212")

	root.grid_rowconfigure(0, weight=1)
	root.grid_rowconfigure(1, weight=0)
	root.grid_columnconfigure(0, weight=3)
	root.grid_columnconfigure(1, weight=1, minsize=inspector_width)

	left_frame = tk.Frame(root, bg="#1e1e1e")
	right_frame = tk.Frame(root, bg="#181818")
	control_bar = tk.Frame(root, bg="#161616", height=140)

	left_frame.grid(row=0, column=0, sticky="nsew", padx=(12, 4), pady=12)
	right_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=12)
	control_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))

	left_frame.grid_propagate(False)
	control_bar.grid_propagate(False)

	audio_manager = AudioManager()
	project_root = Path(__file__).resolve().parent
	cues_path = project_root / "data" / "cues.json"
	audio_dir = project_root / "audio"

	current_track: Path | None = None
	track_length_seconds = 0.0
	is_paused = False
	is_playing = False
	user_is_dragging_seek = False
	ignore_seek_callback = False
	playback_offset_seconds = 0.0
	pending_track_path: Path | None = None
	pending_display_name: str | None = None
	pending_cue_text: str | None = None
	pending_sound: pygame.mixer.Sound | None = None
	pending_autostart = False
	selected_cue_id: str | None = None
	cues_data: dict[str, dict[str, object]] = {}
	suppress_autostart_save = False

	left_title = tk.Label(
		left_frame,
		text="Cue List",
		bg="#1e1e1e",
		fg="#f1f1f1",
		font=("Segoe UI", 20, "bold"),
	)
	left_title.pack(anchor="nw", padx=20, pady=20)

	cue_list_container = tk.Frame(left_frame, bg="#1e1e1e")
	cue_list_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

	cue_scrollbar = tk.Scrollbar(cue_list_container, orient="vertical")
	cue_scrollbar.pack(side="right", fill="y")

	cue_listbox = tk.Listbox(
		cue_list_container,
		bg="#242424",
		fg="#f1f1f1",
		selectbackground="#3b3b3b",
		selectforeground="#ffffff",
		activestyle="none",
		font=("Segoe UI", 11),
		relief="flat",
		highlightthickness=0,
		yscrollcommand=cue_scrollbar.set,
	)
	cue_listbox.pack(side="left", fill="both", expand=True)
	cue_scrollbar.configure(command=cue_listbox.yview)

	cue_entries: list[dict[str, object]] = []

	inspector_title = tk.Label(
		right_frame,
		text="Inspector",
		bg="#181818",
		fg="#f1f1f1",
		font=("Segoe UI", 20, "bold"),
	)
	inspector_title.pack(anchor="nw", padx=20, pady=(20, 8))

	selected_cue_var = tk.StringVar(value="Selected Cue: None")

	track_name_var = tk.StringVar(value="Playing: None")

	status_var = tk.StringVar(value="Status: Idle")
	status_label = tk.Label(
		right_frame,
		textvariable=status_var,
		bg="#181818",
		fg="#9ad0ff",
		font=("Segoe UI", 10),
		anchor="w",
		justify="left",
		wraplength=inspector_content_wrap,
	)
	status_label.pack(fill="x", padx=20, pady=(6, 14))

	autostart_var = tk.BooleanVar(value=False)
	autostart_check = tk.Checkbutton(
		right_frame,
		text="Autostart queued cue after current finishes",
		variable=autostart_var,
		bg="#181818",
		fg="#f1f1f1",
		activebackground="#181818",
		activeforeground="#f1f1f1",
		selectcolor="#242424",
		anchor="w",
		justify="left",
		wraplength=inspector_content_wrap,
	)
	autostart_check.pack(fill="x", padx=20, pady=(0, 10))

	seek_var = tk.DoubleVar(value=0.0)
	time_var = tk.StringVar(value="00:00 / 00:00")
	selected_cue_normal_font = ("Segoe UI", 14, "bold")
	track_name_normal_font = ("Segoe UI", 13)

	def set_status(text: str) -> None:
		status_var.set(f"Status: {text}")

	def set_playing_emphasis(is_currently_playing: bool) -> None:
		_ = is_currently_playing
		selected_cue_label.configure(
			font=selected_cue_normal_font,
		)
		track_name_label.configure(
			font=track_name_normal_font,
		)

	def set_seek_value(seconds: float) -> None:
		nonlocal ignore_seek_callback
		clamped_seconds = max(0.0, min(track_length_seconds, seconds))
		ignore_seek_callback = True
		seek_var.set(clamped_seconds)
		ignore_seek_callback = False
		time_var.set(f"{_format_time(clamped_seconds)} / {_format_time(track_length_seconds)}")

	def save_cues_data() -> None:
		with cues_path.open("w", encoding="utf-8") as cues_file:
			json.dump(cues_data, cues_file, indent=4)

	def on_autostart_toggle() -> None:
		nonlocal cues_data, selected_cue_id, suppress_autostart_save
		if suppress_autostart_save:
			return
		if selected_cue_id is None:
			return
		if selected_cue_id not in cues_data:
			return

		new_autostart = bool(autostart_var.get())
		cues_data[selected_cue_id]["autostart"] = new_autostart
		for cue_entry in cue_entries:
			if str(cue_entry.get("id")) == selected_cue_id:
				cue_entry["autostart"] = new_autostart
				break
		try:
			save_cues_data()
			set_status("Cue autostart updated")
		except Exception as error:
			messagebox.showerror("Cue Save Error", str(error))
			set_status("Cue save failed")

	autostart_check.configure(command=on_autostart_toggle)

	def load_track_path(
		track_path: Path,
		display_name: str | None = None,
		selected_cue_text: str | None = None,
	) -> None:
		nonlocal current_track, track_length_seconds, is_paused, is_playing, playback_offset_seconds
		if not track_path.exists():
			messagebox.showerror("Load Error", f"Audio file not found:\n{track_path}")
			set_status("Load failed")
			return

		try:
			audio_manager.load_track(track_path)
			current_track = track_path
			track_name_var.set(f"Playing: {display_name or current_track.name}")
			if selected_cue_text is None:
				selected_cue_var.set("Selected Cue: External File")
			else:
				selected_cue_var.set(f"Selected Cue: {selected_cue_text}")
			track_length_seconds = float(pygame.mixer.Sound(str(track_path)).get_length())
			seek_scale.configure(to=max(track_length_seconds, 1.0))
			playback_offset_seconds = 0.0
			set_seek_value(0.0)
			is_paused = False
			is_playing = False
			set_playing_emphasis(False)
			set_status("Track loaded")
		except Exception as error:
			messagebox.showerror("Load Error", str(error))
			set_status("Load failed")

	def load_cue_list() -> None:
		nonlocal cue_entries, cues_data
		cue_listbox.delete(0, tk.END)
		cue_entries = []

		try:
			with cues_path.open("r", encoding="utf-8") as cues_file:
				cues_data = json.load(cues_file)

			sorted_items = sorted(
				cues_data.items(),
				key=lambda item: int(item[0]),
			)
			for cue_id, cue in sorted_items:
				name = str(cue.get("name", f"Cue {cue_id}"))
				file_name = str(cue.get("file", ""))
				autostart = bool(cue.get("autostart", False))
				auto_suffix = " [AUTO]" if autostart else ""
				cue_listbox.insert(tk.END, f"{int(cue_id):02d} - {name}{auto_suffix}")
				cue_entries.append({"id": cue_id, "name": name, "file": file_name, "autostart": autostart})
			set_status("Cue list loaded")
		except Exception as error:
			messagebox.showerror("Cue List Error", str(error))
			set_status("Cue list failed")

	def on_cue_activate(_event: tk.Event) -> None:
		nonlocal pending_track_path, pending_display_name, pending_cue_text, pending_sound
		nonlocal pending_autostart, selected_cue_id, suppress_autostart_save
		selection = cue_listbox.curselection()
		if not selection:
			return

		selected_index = selection[0]
		if selected_index >= len(cue_entries):
			return

		cue = cue_entries[selected_index]
		selected_cue_id = str(cue["id"])
		cue_name = str(cue["name"])
		file_name = str(cue["file"])
		cue_autostart = bool(cue.get("autostart", False))
		if not file_name:
			messagebox.showerror("Cue Error", f"Cue '{cue_name}' has no file set.")
			return

		track_path = audio_dir / file_name
		if not track_path.exists():
			messagebox.showerror("Cue Error", f"Audio file not found:\n{track_path}")
			set_status("Cue file missing")
			return

		try:
			# Preload queued cue while current cue keeps playing.
			pending_sound = pygame.mixer.Sound(str(track_path))
		except Exception as error:
			messagebox.showerror("Cue Error", f"Failed to preload cue:\n{error}")
			set_status("Cue preload failed")
			return

		cue_display = f"{int(str(cue['id'])):02d} - {cue_name}"
		pending_track_path = track_path
		pending_display_name = cue_name
		pending_cue_text = cue_display
		pending_autostart = cue_autostart

		suppress_autostart_save = True
		autostart_var.set(cue_autostart)
		suppress_autostart_save = False
		selected_cue_var.set(f"Selected Cue: {cue_display} (queued)")

		if cue_autostart:
			set_status("Cue preloaded (autostart on finish)")
		else:
			set_status("Cue preloaded (press Space to start)")

	def advance_to_next_cue() -> None:
		selection = cue_listbox.curselection()
		if not selection:
			return

		current_index = selection[0]
		next_index = current_index + 1
		if next_index >= len(cue_entries):
			return

		cue_listbox.selection_clear(0, tk.END)
		cue_listbox.selection_set(next_index)
		cue_listbox.activate(next_index)
		cue_listbox.see(next_index)
		cue_listbox.event_generate("<<ListboxSelect>>")

	def switch_to_queued_cue(_event: tk.Event | None = None) -> str | None:
		nonlocal pending_track_path, pending_display_name, pending_cue_text, pending_sound
		nonlocal pending_autostart
		if pending_track_path is None:
			return "break"

		load_track_path(pending_track_path, pending_display_name, pending_cue_text)
		play_track()
		pending_track_path = None
		pending_display_name = None
		pending_cue_text = None
		pending_sound = None
		pending_autostart = False
		advance_to_next_cue()
		return "break"

	def play_track() -> None:
		nonlocal is_paused, is_playing, playback_offset_seconds
		if current_track is None:
			messagebox.showinfo("No Track", "Please load an audio file first.")
			return
		try:
			if not is_paused:
				playback_offset_seconds = 0.0
			audio_manager.play()
			is_paused = False
			is_playing = True
			set_playing_emphasis(True)
			set_status("Playing")
		except Exception as error:
			messagebox.showerror("Play Error", str(error))

	def pause_track() -> None:
		nonlocal is_paused, is_playing
		if current_track is None:
			return
		audio_manager.pause()
		is_paused = True
		is_playing = False
		set_playing_emphasis(False)
		set_status("Paused")

	def resume_track() -> None:
		nonlocal is_paused, is_playing
		if current_track is None:
			return
		if not is_paused:
			set_status("Already playing")
			return
		audio_manager.play()
		is_paused = False
		is_playing = True
		set_playing_emphasis(True)
		set_status("Resumed")

	def stop_track() -> None:
		nonlocal is_paused, is_playing, playback_offset_seconds
		if current_track is None:
			return
		audio_manager.stop()
		playback_offset_seconds = 0.0
		set_seek_value(0.0)
		is_paused = False
		is_playing = False
		set_playing_emphasis(False)
		set_status("Stopped")

	def stop_all_audio_hotkey(_event: tk.Event | None = None) -> str:
		stop_track()
		return "break"

	def seek_track(value: str) -> None:
		nonlocal is_paused, playback_offset_seconds, is_playing
		if current_track is None:
			return
		if user_is_dragging_seek or ignore_seek_callback:
			return

		seconds = float(value)
		try:
			playback_offset_seconds = seconds
			audio_manager.seek(seconds)
			if is_paused:
				audio_manager.pause()
				is_playing = False
			else:
				is_playing = True
			set_seek_value(seconds)
			set_status("Seeked")
		except Exception as error:
			messagebox.showerror("Seek Error", str(error))

	def apply_seek_from_entry() -> None:
		if current_track is None:
			return
		try:
			seconds = float(seek_entry.get())
			seconds = max(0.0, min(track_length_seconds, seconds))
			seek_var.set(seconds)
			seek_track(str(seconds))
		except ValueError:
			messagebox.showerror("Invalid Input", "Enter seek time in seconds.")

	def on_seek_press(_event: tk.Event) -> None:
		nonlocal user_is_dragging_seek
		user_is_dragging_seek = True

	def on_seek_release(_event: tk.Event) -> None:
		nonlocal user_is_dragging_seek
		user_is_dragging_seek = False
		seek_track(str(seek_var.get()))

	def update_seek_progress() -> None:
		nonlocal is_playing, playback_offset_seconds
		if current_track is not None and track_length_seconds > 0 and not user_is_dragging_seek:
			if is_playing:
				if pygame.mixer.music.get_busy():
					position_ms = pygame.mixer.music.get_pos()
					if position_ms >= 0:
						current_seconds = playback_offset_seconds + (position_ms / 1000.0)
						set_seek_value(current_seconds)
				else:
					is_playing = False
					set_playing_emphasis(False)
					playback_offset_seconds = 0.0
					set_seek_value(track_length_seconds)
					set_status("Finished")
					if pending_track_path is not None and pending_autostart:
						switch_to_queued_cue()
		root.after(200, update_seek_progress)

	control_top_row = tk.Frame(control_bar, bg="#161616")
	control_top_row.pack(fill="x", padx=20, pady=(14, 8))

	now_playing_frame = tk.Frame(control_top_row, bg="#161616")
	now_playing_frame.pack(side="left", fill="x", expand=True)

	selected_cue_label = tk.Label(
		now_playing_frame,
		textvariable=selected_cue_var,
		bg="#161616",
		fg="#f1f1f1",
		font=("Segoe UI", 11, "bold"),
		anchor="w",
		justify="left",
	)
	selected_cue_label.pack(fill="x")

	track_name_label = tk.Label(
		now_playing_frame,
		textvariable=track_name_var,
		bg="#161616",
		fg="#cccccc",
		font=("Segoe UI", 11),
		anchor="w",
		justify="left",
	)
	track_name_label.pack(fill="x", pady=(2, 0))

	control_bottom_row = tk.Frame(control_bar, bg="#161616")
	control_bottom_row.pack(fill="x", padx=20, pady=(0, 12))

	transport_row = tk.Frame(control_top_row, bg="#161616")
	transport_row.pack(side="right", anchor="e")

	button_style = {
		"bg": "#2a2a2a",
		"fg": "#f2f2f2",
		"activebackground": "#3a3a3a",
		"activeforeground": "#ffffff",
		"relief": "flat",
		"padx": 12,
		"pady": 8,
	}

	tk_play = tk.Button(transport_row, text="Play", command=play_track, **button_style)
	tk_pause = tk.Button(transport_row, text="Pause", command=pause_track, **button_style)
	tk_resume = tk.Button(transport_row, text="Resume", command=resume_track, **button_style)
	tk_stop = tk.Button(transport_row, text="Stop", command=stop_track, **button_style)

	tk_play.pack(side="left", padx=(0, 8))
	tk_pause.pack(side="left", padx=(0, 8))
	tk_resume.pack(side="left", padx=(0, 8))
	tk_stop.pack(side="left")

	seek_label = tk.Label(
		control_bottom_row,
		text="Seek",
		bg="#161616",
		fg="#f1f1f1",
		font=("Segoe UI", 11, "bold"),
	)
	seek_label.pack(side="left", padx=(0, 10))

	seek_scale = tk.Scale(
		control_bottom_row,
		from_=0,
		to=100,
		orient="horizontal",
		resolution=0.1,
		showvalue=False,
		variable=seek_var,
		command=seek_track,
		bg="#161616",
		fg="#f1f1f1",
		highlightthickness=0,
		troughcolor="#2b2b2b",
		activebackground="#4d4d4d",
		length=520,
	)
	seek_scale.pack(side="left", fill="x", expand=True)
	seek_scale.bind("<ButtonPress-1>", on_seek_press)
	seek_scale.bind("<ButtonRelease-1>", on_seek_release)

	time_label = tk.Label(
		control_bottom_row,
		textvariable=time_var,
		bg="#161616",
		fg="#cccccc",
		font=("Segoe UI", 10),
	)
	time_label.pack(side="left", padx=(12, 10))

	seek_entry_row = tk.Frame(control_bottom_row, bg="#161616")
	seek_entry_row.pack(side="left")

	seek_entry = tk.Entry(
		seek_entry_row,
		bg="#242424",
		fg="#f1f1f1",
		insertbackground="#f1f1f1",
		relief="flat",
		width=8,
	)
	seek_entry.pack(side="left")
	seek_entry.insert(0, "0")

	seek_apply_button = tk.Button(
		seek_entry_row,
		text="Seek (s)",
		command=apply_seek_from_entry,
		bg="#2a2a2a",
		fg="#f2f2f2",
		activebackground="#3a3a3a",
		activeforeground="#ffffff",
		relief="flat",
		padx=12,
		pady=6,
	)
	seek_apply_button.pack(side="left", padx=(10, 0))

	cue_listbox.bind("<<ListboxSelect>>", on_cue_activate)
	cue_listbox.bind("<Double-Button-1>", on_cue_activate)
	cue_listbox.bind("<Return>", on_cue_activate)
	root.bind_all("<space>", switch_to_queued_cue)
	root.bind_all("s", stop_all_audio_hotkey)
	root.bind_all("S", stop_all_audio_hotkey)
	load_cue_list()

	update_seek_progress()
	root.mainloop()


if __name__ == "__main__":
	main()
