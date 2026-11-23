import re
import numpy as np


class WakeWordDetector:
    WAKE_PATTERN = re.compile(
        r"(?:^|\b)(?:hey|hi|hello|ok|okay)?\s*(?:gipsy|gypsy|jipsy|gipsi)[,\s.!?]*(.*)$",
        re.IGNORECASE,
    )

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

    def extract_wake_command(self, text: str) -> tuple[bool, str]:
        if not text:
            return False, ""
        match = self.WAKE_PATTERN.search(text.strip())
        if match:
            cmd = match.group(1).strip()
            cmd = re.sub(r"^[,\s.!?]+|[,\s.!?]+$", "", cmd).strip()
            return True, cmd
        return False, ""

    def reset(self):
        self.buffer.clear()
