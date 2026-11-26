import re
import numpy as np


class WakeWordDetector:
    WAKE_PATTERN = re.compile(
        r"(?:^|\b)(?:"
        r"(?:hey|hi|hello|ok|okay|yo|a)\s*[,.]?\s*(?:gipsy|gypsy|jipsy|gipsi|gibsy|jepsy|jipsi|tipsy|dipsy|chipsy|yipsy)"
        r"|(?:gipsy|gypsy|jipsy|gipsi|gibsy|jepsy)"
        r")[,\s.!?'’]*(.*)$",
        re.IGNORECASE,
    )

    def __init__(self, target_word: str = "gipsy"):
        self.target_word = target_word.lower()
        self.buffer = []

    def process_audio(self, chunk: np.ndarray) -> bool:
        if len(chunk) == 0:
            return False

        peak = np.max(np.abs(chunk))
        return float(peak) > 0.35

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
