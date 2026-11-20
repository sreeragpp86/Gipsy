import asyncio
import numpy as np
import sounddevice as sd
from app.voice.vad import VoiceActivityDetector
from app.voice.wake_word import WakeWordDetector
from app.voice.stt import SpeechToTextEngine


class AudioInputPipeline:
    def __init__(self, sample_rate: int = 16000, block_size: int = 1024):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.vad = VoiceActivityDetector(sample_rate=sample_rate)
        self.wake_detector = WakeWordDetector()
        self.stt = SpeechToTextEngine()

        self.is_recording = False
        self.recorded_chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._loop = None

    def start_capture(self, on_speech_completed):
        self._loop = asyncio.get_running_loop()
        self.recorded_chunks = []
        self.is_recording = True
        self.vad.reset()

        def audio_callback(indata, frames, time_info, status):
            if not self.is_recording:
                return

            chunk = indata[:, 0].copy()
            self.recorded_chunks.append(chunk)

            is_voice, event = self.vad.process_chunk(chunk)
            if event == "SPEECH_END":
                self.is_recording = False
                combined = np.concatenate(self.recorded_chunks)
                self._loop.call_soon_threadsafe(
                    asyncio.create_task, on_speech_completed(combined)
                )

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.block_size,
            callback=audio_callback,
        )
        self._stream.start()

    def stop_capture(self) -> np.ndarray | None:
        self.is_recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self.recorded_chunks:
            audio = np.concatenate(self.recorded_chunks)
            self.recorded_chunks = []
            return audio
        return None
