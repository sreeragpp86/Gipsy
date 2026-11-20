import numpy as np


class WakeWordDetector:
    def __init__(self, target_word: str = "gipsy"):
        self.target_word = target_word.lower()
        self.buffer = []

    def process_audio(self, chunk: np.ndarray) -> bool:
        if len(chunk) == 0:
            return False

        peak = np.max(np.abs(chunk))
        if peak > 0.35:
            return True

        return False

    def reset(self):
        self.buffer.clear()
