"""
Voice Agent — local audio decode to text.  No LLM, no cloud.

Same philosophy as Babel: raw bytes → local decoder → Unicode text.

  Babel:  text bytes  → Python UTF-8 decode  → Unicode string
  Voice:  PCM bytes   → Vosk local decoder   → English string

Audio never leaves the machine.  No API call is made at any point.

Backend cascade (first available wins):
  1. Vosk + sounddevice    — best quality (~40 MB model, auto-downloads once)
  2. Vosk + pyaudio        — same model, different capture library
  3. SpeechRecognition + pocketsphinx — zero model download, lower quality

Install for best results:
  pip install vosk sounddevice
"""
from __future__ import annotations

import io
import json
import urllib.request
import wave
import zipfile
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
_ROOT       = Path(__file__).parent.parent.parent
_VOICE_DIR  = _ROOT / ".cursiv" / "voice"
SAMPLE_RATE = 16_000   # Vosk and Sphinx both expect 16 kHz mono int16

_MODEL_NAME = "vosk-model-small-en-us-0.15"
_MODEL_URL  = f"https://alphacephei.com/vosk/models/{_MODEL_NAME}.zip"
_MODEL_DIR  = _VOICE_DIR / _MODEL_NAME


# ── Model bootstrap (first-use download, ~40 MB) ─────────────────────────────

def _ensure_vosk_model(status_cb=None) -> Path:
    """Download + unzip Vosk model on first use; subsequent calls are instant."""
    if _MODEL_DIR.exists():
        return _MODEL_DIR
    _VOICE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = _VOICE_DIR / f"{_MODEL_NAME}.zip"
    if status_cb:
        status_cb("First-time setup: downloading Vosk voice model (~40 MB)…")
    try:
        urllib.request.urlretrieve(_MODEL_URL, zip_path)
    except Exception as exc:
        raise RuntimeError(f"Model download failed: {exc}") from exc
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(_VOICE_DIR)
    try:
        zip_path.unlink()
    except Exception:
        pass
    if status_cb:
        status_cb("Voice model ready.")
    return _MODEL_DIR


# ── Audio capture ─────────────────────────────────────────────────────────────

def record(duration_s: float = 5.0, status_cb=None) -> bytes:
    """
    Capture `duration_s` seconds from the default microphone.
    Returns raw PCM int16 bytes (mono, 16 kHz).
    Tries sounddevice first, falls back to pyaudio.
    """
    if status_cb:
        status_cb(f"Listening… ({duration_s:.0f}s)")

    # ── sounddevice (preferred) ───────────────────────────────────────────────
    try:
        import sounddevice as _sd
        import numpy as _np
        audio = _sd.rec(
            int(duration_s * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
        )
        _sd.wait()
        return audio.tobytes()
    except ImportError:
        pass

    # ── pyaudio fallback ──────────────────────────────────────────────────────
    try:
        import pyaudio as _pa
        pa     = _pa.PyAudio()
        stream = pa.open(
            format=_pa.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=1024,
        )
        n_frames = int(SAMPLE_RATE / 1024 * duration_s)
        frames   = [stream.read(1024) for _ in range(n_frames)]
        stream.stop_stream()
        stream.close()
        pa.terminate()
        return b"".join(frames)
    except ImportError:
        pass

    raise RuntimeError(
        "No audio capture library found.\n"
        "  pip install sounddevice   (recommended)\n"
        "  pip install pyaudio       (alternative)"
    )


# ── Transcription ─────────────────────────────────────────────────────────────

def transcribe(pcm_bytes: bytes, status_cb=None) -> str:
    """
    Decode PCM audio bytes → text entirely locally.

    Vosk is tried first (best quality).  If vosk is not installed,
    falls back to pocketsphinx via SpeechRecognition.
    Neither path makes any network call.
    """

    # ── Vosk (primary) ────────────────────────────────────────────────────────
    try:
        from vosk import Model, KaldiRecognizer, SetLogLevel  # type: ignore
        SetLogLevel(-1)
        model_path = _ensure_vosk_model(status_cb)
        rec = KaldiRecognizer(Model(str(model_path)), SAMPLE_RATE)
        rec.AcceptWaveform(pcm_bytes)
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip()
    except ImportError:
        pass
    except Exception as exc:
        if status_cb:
            status_cb(f"Vosk error ({exc}) — trying Sphinx fallback")

    # ── SpeechRecognition + pocketsphinx (fallback) ───────────────────────────
    try:
        import speech_recognition as _sr  # type: ignore

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)   # int16 = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm_bytes)
        buf.seek(0)

        r = _sr.Recognizer()
        with _sr.AudioFile(buf) as source:
            audio_data = r.record(source)
        return r.recognize_sphinx(audio_data)
    except ImportError:
        pass
    except Exception as exc:
        if status_cb:
            status_cb(f"Sphinx error: {exc}")

    raise RuntimeError(
        "No voice transcription library found.\n"
        "  pip install vosk sounddevice      (recommended — ~40 MB model)\n"
        "  pip install SpeechRecognition pocketsphinx pyaudio  (zero-download fallback)"
    )


# ── Convenience: record + transcribe in one call ──────────────────────────────

def listen(duration_s: float = 5.0, status_cb=None) -> str:
    """Record then transcribe.  Returns the transcribed text string."""
    pcm = record(duration_s, status_cb)
    return transcribe(pcm, status_cb)


# ── Availability check ────────────────────────────────────────────────────────

def is_available() -> bool:
    """True if at least one capture backend is importable."""
    for pkg in ("sounddevice", "pyaudio"):
        try:
            __import__(pkg)
            return True
        except ImportError:
            pass
    return False


def backend_name() -> str:
    """Return the name of the first available capture backend."""
    try:
        import sounddevice  # noqa: F401
        return "sounddevice"
    except ImportError:
        pass
    try:
        import pyaudio  # noqa: F401
        return "pyaudio"
    except ImportError:
        return "none"
