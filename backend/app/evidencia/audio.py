"""Geração de evidência commitável da modalidade áudio (Épico 10 / ADR 0030)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.azure.audio_nlp import build_audio_modality_risk
from app.azure.critical_terms import find_critical_terms
from app.azure.language import create_language_analyze
from app.azure.provider import AudioAnalysisResult, clear_audio_analysis_cache
from app.azure.speech import create_speech_analyze

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WAV = (
    REPO_ROOT / "data" / "fixtures" / "audio" / "tts" / "audio_tts_critica.wav"
)
DEFAULT_OUT = REPO_ROOT / "data" / "evidencia" / "audio"

# Roteiro espelhado do gerador TTS (dry-run sem Azure).
DRY_RUN_TRANSCRIPT_CRITICA = (
    "Doutor, não estou bem. Estou sentindo uma dor no peito muito forte "
    "e também estou com falta de ar desde ontem à noite. "
    "Tive uma tontura quando levantei e quase desmaiei."
)


@dataclass(frozen=True)
class EvidenciaAudioResult:
    output_dir: Path
    analysis_path: Path
    mode: str


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _analyze_dry_run(wav_path: Path) -> AudioAnalysisResult:
    """Sem rede: Transcrição = roteiro da fixture crítica + Sentimento sintético."""
    _ = wav_path
    transcript = DRY_RUN_TRANSCRIPT_CRITICA
    return AudioAnalysisResult(
        provider="azure",
        transcript=transcript,
        score=0.25,
        sentiment="negative",
        sentiment_scores={
            "positive": 0.05,
            "neutral": 0.15,
            "negative": 0.80,
        },
        key_phrases=("dor no peito", "falta de ar"),
        language_available=True,
    )


def _analyze_live(wav_path: Path) -> AudioAnalysisResult:
    clear_audio_analysis_cache()
    payload = wav_path.read_bytes()
    speech = create_speech_analyze()
    speech_data = speech(payload)
    transcript = str(speech_data.get("transcript", ""))
    score = float(speech_data.get("score", 0.0))
    language = create_language_analyze()(transcript)
    return AudioAnalysisResult(
        provider="azure",
        transcript=transcript,
        score=score,
        sentiment=language.sentiment if language.available else None,
        sentiment_scores=language.sentiment_scores if language.available else None,
        key_phrases=language.key_phrases if language.available else (),
        language_available=language.available,
    )


def build_evidencia_payload(
    analysis: AudioAnalysisResult,
    *,
    wav_path: Path,
    mode: str,
) -> dict[str, Any]:
    risk = build_audio_modality_risk(analysis)
    terms = (
        find_critical_terms(analysis.transcript)
        if analysis.transcript
        else []
    )
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "mode": mode,
        "disclaimer": (
            "Protótipo acadêmico Limen — demonstração, sem diagnóstico clínico."
        ),
        "source_wav": str(wav_path.relative_to(REPO_ROOT))
        if wav_path.is_relative_to(REPO_ROOT)
        else str(wav_path),
        "provider": analysis.provider,
        "transcript": analysis.transcript,
        "language_available": analysis.language_available,
        "sentiment": analysis.sentiment,
        "sentiment_scores": analysis.sentiment_scores,
        "key_phrases": list(analysis.key_phrases),
        "critical_terms": terms,
        "modality_risk": {
            "score": risk.score,
            "level": risk.level,
            "anomalies": [asdict(a) for a in risk.anomalies],
        },
    }


def run_evidencia_audio(
    *,
    wav_path: Path | None = None,
    output_dir: Path | None = None,
    dry_run: bool = False,
) -> EvidenciaAudioResult:
    """Analisa o WAV e grava JSON em `data/evidencia/audio/`."""
    wav = wav_path or DEFAULT_WAV
    out = output_dir or DEFAULT_OUT
    if not wav.is_file():
        raise FileNotFoundError(f"Fixture TTS ausente: {wav}")

    mode = "dry-run" if dry_run else "azure-live"
    analysis = _analyze_dry_run(wav) if dry_run else _analyze_live(wav)
    payload = build_evidencia_payload(analysis, wav_path=wav, mode=mode)

    analysis_path = out / "analysis.json"
    _write_json(analysis_path, payload)
    _write_json(
        out / "transcript.json",
        {
            "transcript": analysis.transcript,
            "provider": analysis.provider,
            "mode": mode,
        },
    )
    _write_json(
        out / "sentiment.json",
        {
            "language_available": analysis.language_available,
            "sentiment": analysis.sentiment,
            "sentiment_scores": analysis.sentiment_scores,
            "key_phrases": list(analysis.key_phrases),
            "mode": mode,
        },
    )
    _write_json(
        out / "critical_terms.json",
        {
            "critical_terms": payload["critical_terms"],
            "mode": mode,
        },
    )
    return EvidenciaAudioResult(output_dir=out, analysis_path=analysis_path, mode=mode)
