from __future__ import annotations

import os
import tempfile
import wave


class VoiceInputError(RuntimeError):
    pass


def _transcribe_audio_bytes(
    audio_bytes: bytes, sample_rate: int, language_code: str
) -> str:
    try:
        import whisper
    except ImportError as exc:
        raise VoiceInputError(
            "Missing whisper package. Install openai-whisper to use STT."
        ) from exc

    model_name = os.getenv("WHISPER_MODEL", "base")
    normalized_lang = language_code.split("-")[0] if language_code else None
    try:
        model = whisper.load_model(model_name)
    except Exception as exc:
        raise VoiceInputError(f"Failed to load Whisper model '{model_name}'.") from exc

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as wav_file:
        wav_file.write(audio_bytes)
        wav_file.flush()
        try:
            result = model.transcribe(wav_file.name, language=normalized_lang)
        except Exception as exc:
            raise VoiceInputError("Whisper transcription failed.") from exc

    text = result.get("text", "") if isinstance(result, dict) else ""
    return text.strip()


def transcribe_audio_bytes(
    audio_bytes: bytes, sample_rate: int, language_code: str
) -> str:
    return _transcribe_audio_bytes(audio_bytes, sample_rate, language_code)


def _read_wav_bytes(path: str) -> tuple[bytes, int]:
    if not os.path.exists(path):
        raise VoiceInputError(f"WAV file not found: {path}")
    with wave.open(path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        if channels != 1:
            raise VoiceInputError("WAV must be mono (1 channel).")
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())
    return frames, sample_rate


def _record_microphone(duration_seconds: int, sample_rate: int) -> bytes | None:
    try:
        import sounddevice as sd
    except ImportError:
        return None
    audio = sd.rec(
        int(duration_seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    return audio.tobytes()


def capture_and_transcribe(
    duration_seconds: int,
    sample_rate: int,
    language_code: str,
    audio_path: str | None = None,
) -> str:
    if audio_path:
        audio_bytes, wav_rate = _read_wav_bytes(audio_path)
        return _transcribe_audio_bytes(audio_bytes, wav_rate, language_code)

    audio_bytes = _record_microphone(duration_seconds, sample_rate)
    if audio_bytes is None:
        raise VoiceInputError(
            "Microphone capture requires the 'sounddevice' package."
        )
    return _transcribe_audio_bytes(audio_bytes, sample_rate, language_code)
