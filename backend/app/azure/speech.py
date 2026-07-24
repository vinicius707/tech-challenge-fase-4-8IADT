"""Cliente Azure Speech (Transcrição pt-BR) — opt-in, injetável, lazy SDK."""

from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

RecognizeFn = Callable[[bytes, str, str, str], str]


def speech_configured_from_environment() -> bool:
    key = os.getenv("AZURE_SPEECH_KEY", "").strip()
    region = os.getenv("AZURE_SPEECH_REGION", "").strip()
    return bool(key and region)


def _score_from_transcript(transcript: str) -> float:
    text = transcript.strip()
    if not text:
        return 0.0
    # Score STT modesto até a fusão NLP (T10.3) aplicar max(acústico, nlp).
    return round(max(0.15, min(0.45, 0.15 + len(text) / 2_000)), 4)


def recognize_with_azure_speech_sdk(
    payload: bytes,
    key: str,
    region: str,
    locale: str,
) -> str:
    """Chama o SDK Azure Speech (rede). Lazy import — CI com Azure off não entra aqui."""
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError as exc:  # pragma: no cover - caminho só com extra instalado
        raise ConnectionError(
            "Pacote azure-cognitiveservices-speech ausente "
            "(uv sync --extra azure-speech)"
        ) from exc

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(payload)
            tmp_path = Path(tmp.name)

        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_recognition_language = locale
        audio_config = speechsdk.audio.AudioConfig(filename=str(tmp_path))
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        segments: list[str] = []
        done = False

        def on_recognized(evt: Any) -> None:
            if (
                evt.result.reason == speechsdk.ResultReason.RecognizedSpeech
                and evt.result.text
            ):
                segments.append(evt.result.text)

        def on_stop(_evt: Any) -> None:
            nonlocal done
            done = True

        recognizer.recognized.connect(on_recognized)
        recognizer.session_stopped.connect(on_stop)
        recognizer.canceled.connect(on_stop)

        recognizer.start_continuous_recognition()
        deadline = time.monotonic() + 90.0
        while not done and time.monotonic() < deadline:
            time.sleep(0.2)
        recognizer.stop_continuous_recognition()

        text = " ".join(segments).strip()
        if not text:
            raise ConnectionError("Azure Speech não retornou Transcrição")
        return text
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def create_speech_analyze(
    *,
    speech_key: str | None = None,
    speech_region: str | None = None,
    locale: str = "pt-BR",
    recognize: RecognizeFn | None = None,
) -> Callable[[bytes], dict[str, Any]]:
    """Factory de `AnalyzeFn` para Speech. Sem key/region → ConnectionError (fallback local)."""
    key = (
        speech_key
        if speech_key is not None
        else os.getenv("AZURE_SPEECH_KEY", "").strip()
    )
    region = (
        speech_region
        if speech_region is not None
        else os.getenv("AZURE_SPEECH_REGION", "").strip()
    )
    recognize_fn = recognize or recognize_with_azure_speech_sdk

    def _analyze(payload: bytes) -> dict[str, Any]:
        if not key or not region:
            raise ConnectionError(
                "Azure Speech não configurado (defina AZURE_SPEECH_KEY e "
                "AZURE_SPEECH_REGION)"
            )
        transcript = recognize_fn(payload, key, region, locale)
        return {
            "transcript": transcript,
            "score": _score_from_transcript(transcript),
        }

    return _analyze
