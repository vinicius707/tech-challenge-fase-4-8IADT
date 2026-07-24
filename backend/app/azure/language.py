"""Cliente Azure Language / Text Analytics (Sentimento + key phrases) — opt-in, injetável."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageAnalysisResult:
    available: bool
    sentiment: str | None = None
    sentiment_scores: dict[str, float] | None = None
    key_phrases: tuple[str, ...] = ()


AnalyzeTextSdkFn = Callable[[str, str, str], LanguageAnalysisResult]
LanguageAnalyzeFn = Callable[[str], LanguageAnalysisResult]


def language_configured_from_environment() -> bool:
    key = os.getenv("AZURE_LANGUAGE_KEY", "").strip()
    endpoint = os.getenv("AZURE_LANGUAGE_ENDPOINT", "").strip()
    return bool(key and endpoint)


def analyze_text_with_azure_language_sdk(
    text: str,
    key: str,
    endpoint: str,
) -> LanguageAnalysisResult:
    """Chama Azure Text Analytics (rede). Lazy import — CI com Azure off não entra aqui."""
    try:
        from azure.ai.textanalytics import TextAnalyticsClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError as exc:  # pragma: no cover
        raise ConnectionError(
            "Pacote azure-ai-textanalytics ausente "
            "(uv sync --extra azure-language)"
        ) from exc

    normalized = endpoint if endpoint.endswith("/") else f"{endpoint}/"
    client = TextAnalyticsClient(
        endpoint=normalized,
        credential=AzureKeyCredential(key),
    )
    docs = [text[:5_000]] if text.strip() else [""]

    sentiment_doc = client.analyze_sentiment(documents=docs, language="pt")[0]
    phrases_doc = client.extract_key_phrases(documents=docs, language="pt")[0]

    if getattr(sentiment_doc, "is_error", False):
        raise ConnectionError("Azure Language falhou na análise de Sentimento")
    if getattr(phrases_doc, "is_error", False):
        raise ConnectionError("Azure Language falhou na extração de key phrases")

    scores: dict[str, float] = {}
    confidence = getattr(sentiment_doc, "confidence_scores", None)
    if confidence is not None:
        scores = {
            "positive": float(confidence.positive),
            "neutral": float(confidence.neutral),
            "negative": float(confidence.negative),
        }

    phrases = tuple(str(p) for p in getattr(phrases_doc, "key_phrases", []) or ())
    return LanguageAnalysisResult(
        available=True,
        sentiment=str(getattr(sentiment_doc, "sentiment", "unknown")),
        sentiment_scores=scores or None,
        key_phrases=phrases,
    )


def create_language_analyze(
    *,
    language_key: str | None = None,
    language_endpoint: str | None = None,
    analyze_text: AnalyzeTextSdkFn | None = None,
) -> LanguageAnalyzeFn:
    """Factory Language. Sem key/endpoint → `available=False` (não levanta)."""
    key = (
        language_key
        if language_key is not None
        else os.getenv("AZURE_LANGUAGE_KEY", "").strip()
    )
    endpoint = (
        language_endpoint
        if language_endpoint is not None
        else os.getenv("AZURE_LANGUAGE_ENDPOINT", "").strip()
    )
    analyze_fn = analyze_text or analyze_text_with_azure_language_sdk

    def _analyze(text: str) -> LanguageAnalysisResult:
        if not key or not endpoint:
            return LanguageAnalysisResult(available=False)
        return analyze_fn(text, key, endpoint)

    return _analyze


def default_language_analyze(text: str) -> LanguageAnalysisResult:
    """Language via env (T10.2). Sem credenciais → indisponível; falhas sobem ao caller."""
    return create_language_analyze()(text)


def empty_language_result() -> LanguageAnalysisResult:
    return LanguageAnalysisResult(available=False)
