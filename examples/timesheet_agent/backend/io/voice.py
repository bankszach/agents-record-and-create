"""Optional voice input/output stubs.

These are placeholders to keep the example dependency-light. Real
implementations would integrate STT/TTS backends behind these interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Represents the result of speech-to-text transcription."""

    text: str
    confidence: float | None = None


class SpeechToText:
    """Abstract STT interface."""

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe audio to text.

        This is a stub. Replace with a concrete implementation as needed.
        """
        return TranscriptionResult(text="", confidence=None)


class TextToSpeech:
    """Abstract TTS interface."""

    def synthesize(self, text: str) -> bytes:
        """Synthesize speech from text and return audio bytes.

        This is a stub. Replace with a concrete implementation as needed.
        """
        return b""
