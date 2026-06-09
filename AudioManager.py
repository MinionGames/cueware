from pathlib import Path

import pygame


class AudioManager:
	def __init__(self) -> None:
		pygame.mixer.init()
		self._current_track: Path | None = None
		self._is_paused = False

	def load_track(self, file_path: str | Path) -> None:
		track_path = Path(file_path)
		if not track_path.exists():
			raise FileNotFoundError(f"Audio file not found: {track_path}")

		pygame.mixer.music.load(str(track_path))
		self._current_track = track_path
		self._is_paused = False

	def play(self) -> None:
		if self._current_track is None:
			raise RuntimeError("No track loaded. Call load_track() first.")

		if self._is_paused:
			pygame.mixer.music.unpause()
			self._is_paused = False
			return

		pygame.mixer.music.play()

	def pause(self) -> None:
		if pygame.mixer.music.get_busy():
			pygame.mixer.music.pause()
			self._is_paused = True

	def stop(self) -> None:
		pygame.mixer.music.stop()
		self._is_paused = False

	def seek(self, seconds: float) -> None:
		if self._current_track is None:
			raise RuntimeError("No track loaded. Call load_track() first.")
		if seconds < 0:
			raise ValueError("Seek position must be >= 0.")

		# pygame seek works by starting playback from a given offset.
		was_paused = self._is_paused
		pygame.mixer.music.play(start=seconds)
		if was_paused:
			pygame.mixer.music.pause()
			self._is_paused = True
		else:
			self._is_paused = False

	def set_volume(self, volume: float) -> None:
		clamped_volume = max(0.0, min(1.0, float(volume)))
		pygame.mixer.music.set_volume(clamped_volume)
