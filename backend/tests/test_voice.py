import asyncio
import numpy as np
import pytest
from app.voice.vad import VoiceActivityDetector
from app.voice.wake_word import WakeWordDetector
from app.voice.tts import SentenceChunker, TextToSpeechEngine
from app.voice.stt import SpeechToTextEngine


def test_sentence_chunker_punctuation():
    chunker = SentenceChunker()
    tokens = ["Opening ", "Terminal. ", "Ready ", "for ", "input! ", "Standing by."]
    collected = []
    for t in tokens:
        sentences = chunker.add_token(t)
        collected.extend(sentences)

    assert "Opening Terminal." in collected
    assert "Ready for input!" in collected
    assert "Standing by." in collected or chunker.flush() == "Standing by."


def test_voice_activity_detector_silence_and_speech():
    vad = VoiceActivityDetector(sample_rate=16000, energy_threshold=0.02)
    silence = np.zeros(1600, dtype=np.float32)
    is_voice, event = vad.process_chunk(silence)
    assert is_voice is False

    t = np.linspace(0, 0.1, 1600, endpoint=False, dtype=np.float32)
    speech = 0.5 * np.sin(2 * np.pi * 440 * t)
    is_voice, event = vad.process_chunk(speech)
    assert is_voice is True
    assert event == "SPEECH_START"


def test_wake_word_detector():
    detector = WakeWordDetector("gipsy")
    quiet = np.zeros(1600, dtype=np.float32)
    assert detector.process_audio(quiet) is False

    loud = np.ones(1600, dtype=np.float32) * 0.5
    assert detector.process_audio(loud) is True

    has_wake, cmd = detector.extract_wake_command("Hey Gipsy, open Safari.")
    assert has_wake is True
    assert cmd == "open Safari"

    has_wake, cmd = detector.extract_wake_command("hey gypsy")
    assert has_wake is True
    assert cmd == ""

    has_wake, cmd = detector.extract_wake_command("Gipsy, set volume to 50")
    assert has_wake is True
    assert cmd == "set volume to 50"

    has_wake, cmd = detector.extract_wake_command("Random background conversation")
    assert has_wake is False
    assert cmd == ""


def test_tts_queue_lifecycle():
    async def run():
        engine = TextToSpeechEngine(voice="Moira")
        await engine.enqueue_sentence("Test sentence one.")
        await engine.finish_stream()

        first = await engine.queue.get()
        assert first == "Test sentence one."
        second = await engine.queue.get()
        assert second is None

    asyncio.run(run())


def test_kokoro_model_discovery():
    engine = TextToSpeechEngine()
    kokoro = engine._get_kokoro()
    assert kokoro is not None
