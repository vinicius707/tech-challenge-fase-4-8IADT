"""TDD T10.3 — Termos Críticos locais, score max(acústico, nlp) e Anomalias de áudio."""

from __future__ import annotations

from app.azure.audio_nlp import (
    NEGATIVE_SENTIMENT_THRESHOLD,
    NLP_SCORE_BOTH,
    NLP_SCORE_SENTIMENT,
    NLP_SCORE_TERMS,
    build_audio_modality_risk,
    is_real_transcript,
)
from app.azure.critical_terms import find_critical_terms
from app.azure.provider import AudioAnalysisResult
from app.cases.vitals_engine import risk_level_from_score


def test_find_critical_terms_matches_accent_insensitive() -> None:
    found = find_critical_terms("Paciente com Falta de Ar e dor no peito.")
    assert "falta de ar" in found
    assert "dor no peito" in found


def test_find_critical_terms_ignores_unrelated_text() -> None:
    assert find_critical_terms("consulta de rotina sem queixas") == []


def test_is_real_transcript_rejects_local_placeholder() -> None:
    assert is_real_transcript("local-transcript-abcdef12") is False
    assert is_real_transcript("paciente com falta de ar") is True


def test_local_placeholder_keeps_acoustic_score_without_nlp_anomalies() -> None:
    analysis = AudioAnalysisResult(
        provider="local",
        transcript="local-transcript-deadbeef",
        score=0.22,
        sentiment="negative",
        sentiment_scores={"negative": 0.9},
        language_available=True,
    )
    risk = build_audio_modality_risk(analysis)
    assert risk.score == 0.22
    assert risk.level == risk_level_from_score(0.22)
    assert risk.anomalies == ()


def test_critical_terms_raise_nlp_score_and_anomaly() -> None:
    analysis = AudioAnalysisResult(
        provider="azure",
        transcript="relato de falta de ar há duas horas",
        score=0.25,
    )
    risk = build_audio_modality_risk(analysis)
    assert risk.score == NLP_SCORE_TERMS
    assert risk.level == "ALTO"
    assert len(risk.anomalies) == 1
    assert risk.anomalies[0].metric == "critical_terms"
    assert risk.anomalies[0].value == 1.0
    assert "falta de ar" in risk.anomalies[0].detail


def test_strong_negative_sentiment_raises_score_and_anomaly() -> None:
    analysis = AudioAnalysisResult(
        provider="azure",
        transcript="estou me sentindo péssimo hoje",
        score=0.20,
        sentiment="negative",
        sentiment_scores={
            "positive": 0.05,
            "neutral": 0.15,
            "negative": NEGATIVE_SENTIMENT_THRESHOLD,
        },
        language_available=True,
    )
    risk = build_audio_modality_risk(analysis)
    assert risk.score == NLP_SCORE_SENTIMENT
    assert risk.level == "MEDIO"
    assert len(risk.anomalies) == 1
    assert risk.anomalies[0].metric == "sentiment_negative"
    assert risk.anomalies[0].value == NEGATIVE_SENTIMENT_THRESHOLD


def test_terms_and_negative_sentiment_combine_to_higher_score() -> None:
    analysis = AudioAnalysisResult(
        provider="azure",
        transcript="dor no peito e falta de ar",
        score=0.30,
        sentiment="negative",
        sentiment_scores={"positive": 0.0, "neutral": 0.1, "negative": 0.9},
        language_available=True,
    )
    risk = build_audio_modality_risk(analysis)
    assert risk.score == NLP_SCORE_BOTH
    assert {a.metric for a in risk.anomalies} == {
        "critical_terms",
        "sentiment_negative",
    }


def test_terms_still_fire_when_language_unavailable() -> None:
    analysis = AudioAnalysisResult(
        provider="azure",
        transcript="dispneia intensa",
        score=0.18,
        language_available=False,
        sentiment=None,
    )
    risk = build_audio_modality_risk(analysis)
    assert risk.score == NLP_SCORE_TERMS
    assert any(a.metric == "critical_terms" for a in risk.anomalies)
    assert not any(a.metric == "sentiment_negative" for a in risk.anomalies)


def test_max_keeps_higher_acoustic_score_when_nlp_lower() -> None:
    analysis = AudioAnalysisResult(
        provider="azure",
        transcript="estou bem, sem queixas",
        score=0.80,
        sentiment="positive",
        sentiment_scores={"positive": 0.8, "neutral": 0.15, "negative": 0.05},
        language_available=True,
    )
    risk = build_audio_modality_risk(analysis)
    assert risk.score == 0.80
    assert risk.anomalies == ()


def test_cache_provider_with_real_transcript_still_gets_nlp() -> None:
    analysis = AudioAnalysisResult(
        provider="cache",
        transcript="paciente com confusão mental",
        score=0.21,
    )
    risk = build_audio_modality_risk(analysis)
    assert risk.score == NLP_SCORE_TERMS
    assert risk.anomalies[0].metric == "critical_terms"
