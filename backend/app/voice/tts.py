import asyncio
import os
import re
import subprocess
from pathlib import Path
import numpy as np
import sounddevice as sd

KOKORO_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "kokoro"
KOKORO_MODEL_FILE = KOKORO_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES_FILE = KOKORO_DIR / "voices-v1.0.bin"


class SentenceChunker:
    def __init__(self):
        self.buffer = ""
        self.sentence_regex = re.compile(r"([^.!?]+[.!?])(?:\s+|$)", re.UNICODE)

    def add_token(self, token: str) -> list[str]:
        self.buffer += token
        sentences = []

        while True:
            match = self.sentence_regex.search(self.buffer)
            if not match:
                break
            sentence = match.group(1).strip()
            if sentence:
                sentences.append(sentence)
            self.buffer = self.buffer[match.end():]

        return sentences

    def flush(self) -> str | None:
        rem = self.buffer.strip()
        self.buffer = ""
        return rem if rem else None


class TextToSpeechEngine:
    def __init__(self, voice: str = "bf_emma", speed: float = 1.05):
        self.voice = os.getenv("GIPSY_VOICE", voice)
        self.speed = float(os.getenv("GIPSY_VOICE_SPEED", str(speed)))
        self.queue: asyncio.Queue[str | None] = asyncio.Queue()
        self.is_playing = False
        self._worker_task: asyncio.Task | None = None
        self._kokoro = None

    def _get_kokoro(self):
        if self._kokoro is None and KOKORO_MODEL_FILE.exists() and KOKORO_VOICES_FILE.exists():
            try:
                from kokoro_onnx import Kokoro
                self._kokoro = Kokoro(str(KOKORO_MODEL_FILE), str(KOKORO_VOICES_FILE))
            except Exception:
                self._kokoro = None
        return self._kokoro

    def start_worker(self, manager):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._playback_worker(manager))

    async def enqueue_sentence(self, sentence: str):
        await self.queue.put(sentence)

    async def finish_stream(self):
        await self.queue.put(None)

    async def _emit_speech_amplitudes(self, manager, duration: float):
        steps = int(duration / 0.05)
        for i in range(steps):
            amplitude = 0.3 + 0.6 * abs(float(((i % 6) - 3) / 3.0))
            await manager.broadcast({
                "type": "audio_amplitude",
                "amplitude": round(amplitude, 2),
            })
            await asyncio.sleep(0.05)
        await manager.broadcast({"type": "audio_amplitude", "amplitude": 0.0})

    async def _speak_with_kokoro(self, text: str, manager, kokoro) -> bool:
        try:
            samples, sample_rate = await asyncio.to_thread(
                kokoro.create,
                text,
                voice=self.voice,
                speed=self.speed,
                lang="en-gb" if self.voice.startswith("bf_") else "en-us",
            )
            if samples is None or len(samples) == 0:
                return False

            duration = len(samples) / sample_rate
            amp_task = asyncio.create_task(self._emit_speech_amplitudes(manager, duration))

            await asyncio.to_thread(sd.play, samples, sample_rate)
            await asyncio.to_thread(sd.wait)
            await amp_task
            return True
        except Exception as e:
            await manager.broadcast({
                "type": "log",
                "level": "system",
                "message": f"Kokoro speech error: {str(e)}",
            })
            return False

    async def _speak_with_macos_say(self, text: str, manager):
        approx_duration = max(0.8, len(text) * 0.065)
        amp_task = asyncio.create_task(self._emit_speech_amplitudes(manager, approx_duration))

        proc = await asyncio.create_subprocess_exec(
            "say",
            "-v",
            "Moira",
            "-r",
            "185",
            text,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await proc.wait()
        await amp_task

    async def _speak_sentence(self, text: str, manager):
        clean_text = text.replace("*", "").replace("#", "").strip()
        if not clean_text:
            return

        kokoro = self._get_kokoro()
        if kokoro is not None:
            success = await self._speak_with_kokoro(clean_text, manager, kokoro)
            if success:
                return

        await self._speak_with_macos_say(clean_text, manager)

    async def _playback_worker(self, manager):
        while True:
            sentence = await self.queue.get()
            if sentence is None:
                self.is_playing = False
                await manager.broadcast({
                    "type": "state_change",
                    "state": "IDLE",
                })
                break

            self.is_playing = True
            await manager.broadcast({
                "type": "state_change",
                "state": "SPEAKING",
            })
            await self._speak_sentence(sentence, manager)
            self.queue.task_done()
