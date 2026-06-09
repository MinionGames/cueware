# Cueware

Cueware is a desktop audio cue runner for live shows and rehearsals.

It provides:
- A Cue List loaded from JSON
- A queued next-cue workflow
- Manual and autostart cue transitions
- Bottom transport controls (play/pause/resume/stop/seek)
- Keyboard shortcuts for fast operation

## Features

- Load cues from `data/cues.json`
- Select a cue to preload it as the next cue
- Start the queued cue with Space
- Optional per-cue autostart when the current cue finishes
- Auto-advance cue selection after starting a cue
- Seek slider with live playback progress
- Numeric seek input in seconds
- Global stop hotkey

## Project Structure

- `main.py` - Tkinter UI and cue workflow logic
- `AudioManager.py` - pygame-based playback wrapper
- `data/cues.json` - cue metadata (id, name, file, autostart)
- `audio/` - audio assets referenced by `data/cues.json`

## Requirements

- Python 3.10+
- pygame

Install dependency:

```bash
pip install pygame
```

## Run

```bash
python main.py
```

## How Cue Flow Works

1. Click a cue in Cue List.
2. Cue is preloaded as queued cue (current cue keeps playing).
3. Press Space to switch/start queued cue.
4. After switch, selection auto-moves to next cue and preloads it.
5. If queued cue has `autostart: true`, it starts automatically when current cue finishes.

## Controls

### Buttons

- Play
- Pause
- Resume
- Stop
- Seek (s)

### Seek

- Drag seek slider
- Or type seconds and press Seek (s)

### Keyboard Shortcuts

- Space: Start queued cue
- S: Stop all audio

## Cue JSON Format

`data/cues.json` is an object keyed by cue number as a string.

Example:

```json
{
	"1": {
		"id": 1,
		"name": "Overture",
		"file": "01_Overture.wav",
		"autostart": false
	}
}
```

Fields:
- `id` (number): cue id
- `name` (string): display name
- `file` (string): file name under `audio/`
- `autostart` (boolean): if true, queued cue auto-starts after current cue ends

## Notes

- Cue list shows `[AUTO]` for cues with `autostart: true`.
- If a file listed in `data/cues.json` is missing from `audio/`, Cueware shows an error dialog.

## Troubleshooting

- If app opens but no sound:
	- Verify system output device
	- Verify `pygame` is installed in the same Python environment
- If a cue fails to load:
	- Check file name matches exactly in `data/cues.json`
	- Confirm the file exists in `audio/`
