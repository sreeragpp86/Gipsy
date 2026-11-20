import asyncio
import re
import subprocess
from datetime import datetime, timezone


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
    def __init__(self, voice: str = "Moira", rate: int = 185):
        self.voice = voice
        self.rate = rate
        self.queue: asyncio.Queue[str | None] = asyncio.Queue()
        self.is_playing = False
        self._worker_task: asyncio.Task | None = None

    def start_worker(self, manager):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._playback_worker(manager))

    async def enqueue_sentence(self, sentence: str):
        await self.queue.put(sentence)

    async def finish_stream(self):
        await self.queue.put(None)

    async def _emit_speech_amplitudes(self, manager, duration: float):
        steps = int(duration / 0.06)
        for i in range(steps):
            amplitude = 0.35 + 0.55 * abs(float(((i % 7) - 3) / 3.0))
            await manager.broadcast({
                "type": "audio_amplitude",
                "amplitude": round(amplitude, 2),
            })
            await asyncio.sleep(0.06)
        await manager.broadcast({"type": "audio_amplitude", "amplitude": 0.0})

    async def _speak_sentence(self, text: str, manager):
        clean_text = text.replace("*", "").replace("#", "").strip()
        if not clean_text:
            return

        approx_duration = max(0.8, len(clean_text) * 0.065)

        amp_task = asyncio.create_task(self._emit_speech_amplitudes(manager, approx_duration))

        proc = await asyncio.create_subprocess_exec(
            "say",
            "-v",
            self.voice,
            "-r",
            str(self.rate),
            clean_text,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        await proc.wait()
        await amp_task

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
