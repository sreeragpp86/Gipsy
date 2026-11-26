import asyncio
import collections
import time
import numpy as np
import sounddevice as sd
from app.voice.stt import SpeechToTextEngine
from app.voice.vad import VoiceActivityDetector
from app.voice.wake_word import WakeWordDetector


class AudioInputPipeline:
    def __init__(
        self,
        sample_rate: int = 16000,
        block_size: int = 1024,
        max_duration_sec: float = 15.0,
        max_buffer_bytes: int = 4 * 1024 * 1024,
    ):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_duration_sec = max_duration_sec
        self.max_chunks = max(1, int(self.sample_rate * self.max_duration_sec / self.block_size))
        self.max_buffer_bytes = max_buffer_bytes
        self.vad = VoiceActivityDetector(sample_rate=sample_rate)
        self.wake_detector = WakeWordDetector()
        self.stt = SpeechToTextEngine()

        self.is_muted = False
        self.is_paused = False
        self._active_mode = False
        self._active_mode_expiry = 0.0

        self.is_recording = False
        self.recorded_chunks: list[np.ndarray] = []
        self._preroll = collections.deque(maxlen=6)
        self._stream: sd.InputStream | None = None
        self._loop = None
        self._on_speech_completed = None
        self._on_amplitude = None
        self._last_amp_time = 0.0
        self._tts_guard = None

    def set_tts_guard(self, guard_fn):
        self._tts_guard = guard_fn

    def mute(self, is_muted: bool):
        self.is_muted = is_muted
        if is_muted:
            self.pause_listening()
        else:
            if self._on_speech_completed and (self._stream is None or not self._stream.active):
                try:
                    self.start_listening(self._on_speech_completed, self._on_amplitude)
                except Exception:
                    self.resume_listening()
            else:
                self.resume_listening()

    def pause_listening(self):
        self.is_paused = True
        self.is_recording = False
        self.recorded_chunks = []
        self.vad.reset()

    def resume_listening(self):
        self.is_recording = False
        self.recorded_chunks = []
        self._preroll.clear()
        self.vad.reset()
        self.is_paused = False

    def set_active_mode(self, duration: float = 8.0):
        self._active_mode = True
        self._active_mode_expiry = time.time() + duration

    def reset_active_mode(self):
        self._active_mode = False
        self._active_mode_expiry = 0.0

    def is_active_mode(self) -> bool:
        if self._active_mode and time.time() < self._active_mode_expiry:
            return True
        self._active_mode = False
        return False

    def reset_buffer(self):
        self.recorded_chunks = []
        self._preroll.clear()

    def _dispatch_speech(self, audio: np.ndarray):
        if self._on_speech_completed:
            asyncio.create_task(self._on_speech_completed(audio))

    def _audio_callback(self, indata, frames, time_info, status):
        if self.is_muted or self.is_paused:
            return

        if self._tts_guard is not None:
            try:
                if self._tts_guard():
                    return
            except Exception:
                pass

        chunk = indata[:, 0].copy()

        rms = float(np.sqrt(np.mean(chunk**2)))
        now = time.time()
        if self._on_amplitude and (now - self._last_amp_time > 0.05):
            self._last_amp_time = now
            if self._loop and self._loop.is_running():
                scaled_amp = min(1.0, round(rms * 14.0, 2))
                self._loop.call_soon_threadsafe(self._on_amplitude, scaled_amp)

        _, event = self.vad.process_chunk(chunk)

        if self.is_recording:
            self.recorded_chunks.append(chunk)
            current_bytes = len(self.recorded_chunks) * self.block_size * 4
            if (
                event == "SPEECH_END"
                or len(self.recorded_chunks) >= self.max_chunks
                or current_bytes >= self.max_buffer_bytes
            ):
                self.is_recording = False
                if self.recorded_chunks:
                    combined = np.concatenate(self.recorded_chunks)
                    self.recorded_chunks = []
                    if self._loop and self._loop.is_running():
                        self._loop.call_soon_threadsafe(self._dispatch_speech, combined)
        else:
            if event == "SPEECH_START":
                self.is_recording = True
                self.recorded_chunks = list(self._preroll)
                self.recorded_chunks.append(chunk)
                self._preroll.clear()
            else:
                self._preroll.append(chunk)

    def start_listening(self, on_speech_completed, on_amplitude=None):
        self.stop_listening()
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()

        self._on_speech_completed = on_speech_completed
        self._on_amplitude = on_amplitude
        self.resume_listening()

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.block_size,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop_listening(self):
        self.is_recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.recorded_chunks = []
        self._preroll.clear()

    def start_capture(self, on_speech_completed):
        self.set_active_mode(12.0)
        self.start_listening(on_speech_completed)

    def stop_capture(self) -> np.ndarray | None:
        chunks = list(self.recorded_chunks)
        self.stop_listening()
        if chunks:
            return np.concatenate(chunks)
        return None
