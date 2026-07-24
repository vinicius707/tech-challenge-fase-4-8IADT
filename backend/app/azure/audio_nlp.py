"""Fusão NLP da modalidade áudio: Termos Críticos + Sentimento → Anomalias e score."""

from __future__ import annotations

from app.azure.critical_terms import find_critical_terms
from app.azure.provider import AudioAnalysisResult
from app.cases.vitals_engine import ModalityRisk, VitalsAnomaly, risk_level_from_score

# Limiares da spec E10 (cenários 4–5).
NLP_SCORE_TERMS = 0.70
NLP_SCORE_SENTIMENT = 0.55
NLP_SCORE_BOTH = 0.85
NEGATIVE_SENTIMENT_THRESHOLD = 0.60


def is_real_transcript(transcript: str) -> bool:
    """Placeholder local do E6.2 não é Transcrição — não dispara NLP."""
    text = transcript.strip()
    return bool(text) and not text.startswith("local-transcript-")


def build_audio_modality_risk(analysis: AudioAnalysisResult) -> ModalityRisk:
    """Score = max(acústico/stt, nlp); Anomalias só sobre Transcrição real."""
    acoustic = float(analysis.score)
    anomalies: list[VitalsAnomaly] = []
    has_terms = False
    has_negative_sentiment = False

    if is_real_transcript(analysis.transcript):
        terms = find_critical_terms(analysis.transcript)
        if terms:
            has_terms = True
            anomalies.append(
                VitalsAnomaly(
                    metric="critical_terms",
                    value=float(len(terms)),
                    detail=f"Termos críticos na fala: {', '.join(terms)}",
                )
            )

        if analysis.language_available and analysis.sentiment == "negative":
            negative = float((analysis.sentiment_scores or {}).get("negative", 0.0))
            if negative >= NEGATIVE_SENTIMENT_THRESHOLD:
                has_negative_sentiment = True
                anomalies.append(
                    VitalsAnomaly(
                        metric="sentiment_negative",
                        value=negative,
                        detail=(
                            "Sentimento fortemente negativo "
                            f"(score {negative:.2f})"
                        ),
                    )
                )

    nlp = 0.0
    if has_terms and has_negative_sentiment:
        nlp = NLP_SCORE_BOTH
    elif has_terms:
        nlp = NLP_SCORE_TERMS
    elif has_negative_sentiment:
        nlp = NLP_SCORE_SENTIMENT

    score = max(acoustic, nlp)
    return ModalityRisk(
        score=score,
        level=risk_level_from_score(score),
        anomalies=tuple(anomalies),
    )
