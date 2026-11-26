import numpy as np


class SpeechToTextEngine:
    INITIAL_PROMPT = "Hey Gipsy, open Safari, terminal, calculator, telemetry, battery, screen."

    def __init__(self, model_size: str = "tiny.en", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
        return self._model

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        if len(audio_data) == 0:
            return ""

        model = self._get_model()

        if audio_data.dtype != np.float32:
            audio_float = audio_data.astype(np.float32) / 32768.0
        else:
            audio_float = audio_data

        # Secondary vad_filter is disabled because VoiceActivityDetector already segments utterances
        segments, _ = model.transcribe(
            audio_float,
            beam_size=1,
            language="en",
            vad_filter=False,
            initial_prompt=self.INITIAL_PROMPT,
        )
        return " ".join(seg.text for seg in segments).strip()
