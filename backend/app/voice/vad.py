import numpy as np


class VoiceActivityDetector:
    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold: float = 0.007,
        silence_duration_ms: int = 600,
    ):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_limit_samples = int((silence_duration_ms / 1000.0) * sample_rate)
        self.is_speech_active = False
        self.silence_samples_count = 0

    def compute_energy(self, chunk: np.ndarray) -> float:
        if len(chunk) == 0:
            return 0.0
        return float(np.sqrt(np.mean(chunk**2)))

    def process_chunk(self, chunk: np.ndarray) -> tuple[bool, str | None]:
        energy = self.compute_energy(chunk)
        is_voice = energy > self.energy_threshold

        event = None

        if is_voice:
            self.silence_samples_count = 0
            if not self.is_speech_active:
                self.is_speech_active = True
                event = "SPEECH_START"
        else:
            if self.is_speech_active:
                self.silence_samples_count += len(chunk)
                if self.silence_samples_count >= self.silence_limit_samples:
                    self.is_speech_active = False
                    self.silence_samples_count = 0
                    event = "SPEECH_END"

        return is_voice, event

    def reset(self):
        self.is_speech_active = False
        self.silence_samples_count = 0
