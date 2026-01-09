from __future__ import annotations

import os
import tempfile
import wave

class VoiceInputError(RuntimeError):
    """음성 입력 관련 오류 클래스입니다."""
    pass

def _transcribe_audio_bytes(
    audio_bytes: bytes, sample_rate: int, language_code: str
) -> str:
    """오디오 바이트를 Whisper 모델을 사용하여 텍스트로 변환합니다."""
    try:
        import whisper
    except ImportError as exc:
        raise VoiceInputError(
            "Whisper 패키지가 없습니다. STT를 사용하려면 openai-whisper를 설치하세요."
        ) from exc

    model_name = os.getenv("WHISPER_MODEL", "base")
    normalized_lang = language_code.split("-")[0] if language_code else None
    try:
        model = whisper.load_model(model_name)
    except Exception as exc:
        raise VoiceInputError(f"Whisper 모델 '{model_name}'을 로드하지 못했습니다.") from exc

    # 임시 파일을 생성하여 오디오 데이터를 저장한 후 변환합니다. (Windows 호환성 위해 delete=False 및 close 처리)
    wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_path = wav_file.name
    try:
        wav_file.write(audio_bytes)
        wav_file.close() # ffmpeg가 접근할 수 있도록 파일을 닫습니다.
        try:
            result = model.transcribe(wav_path, language=normalized_lang)
        except Exception as exc:
            raise VoiceInputError("Whisper 변환 중 오류가 발생했습니다.") from exc
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

    text = result.get("text", "") if isinstance(result, dict) else ""
    return text.strip()

def transcribe_audio_bytes(
    audio_bytes: bytes, sample_rate: int, language_code: str
) -> str:
    """오디오 바이트 변환 함수를 호출합니다."""
    return _transcribe_audio_bytes(audio_bytes, sample_rate, language_code)

def _read_wav_bytes(path: str) -> tuple[bytes, int]:
    """WAV 파일에서 오디오 바이트와 샘플링 레이트를 읽어옵니다."""
    if not os.path.exists(path):
        raise VoiceInputError(f"WAV 파일을 찾을 수 없습니다: {path}")
    with wave.open(path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        if channels != 1:
            raise VoiceInputError("WAV 파일은 반드시 모노(1 채널)여야 합니다.")
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())
    return frames, sample_rate

def _record_microphone(duration_seconds: int, sample_rate: int) -> bytes | None:
    """마이크로부터 오디오를 녹음합니다."""
    try:
        import sounddevice as sd
    except ImportError:
        return None
    # 지정된 시간 동안 녹음 실행
    audio = sd.rec(
        int(duration_seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
    )
    sd.wait() # 녹음이 끝날 때까지 대기
    return audio.tobytes()

def capture_and_transcribe(
    duration_seconds: int,
    sample_rate: int,
    language_code: str,
    audio_path: str | None = None,
) -> str:
    """음성 캡처 및 변환을 총괄하는 함수입니다."""
    if audio_path:
        # 파일로부터 변환
        audio_bytes, wav_rate = _read_wav_bytes(audio_path)
        return _transcribe_audio_bytes(audio_bytes, wav_rate, language_code)

    # 마이크로부터 녹음 후 변환
    audio_bytes = _record_microphone(duration_seconds, sample_rate)
    if audio_bytes is None:
        raise VoiceInputError(
            "마이크 캡처를 위해서는 'sounddevice' 패키지가 필요합니다."
        )
    return _transcribe_audio_bytes(audio_bytes, sample_rate, language_code)
