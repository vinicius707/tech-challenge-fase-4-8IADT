"""Lista determinística PT-BR de Termos Críticos (sempre local; Épico 10 / ADR 0031)."""

from __future__ import annotations

import re
import unicodedata

# Heurísticas demonstrativas — não são protocolo clínico validado.
CRITICAL_TERMS_PT: tuple[str, ...] = (
    "falta de ar",
    "dispneia",
    "dificuldade para respirar",
    "cianose",
    "taquipneia",
    "saturação baixa",
    "dessaturação",
    "dor no peito",
    "dor torácica",
    "palpitação",
    "taquicardia",
    "bradicardia",
    "hipotensão",
    "hipertensão severa",
    "confusão mental",
    "sonolência excessiva",
    "perda de consciência",
    "desmaio",
    "convulsão",
    "tontura intensa",
    "fraqueza súbita",
    "dormência",
    "cansaço extremo",
    "fadiga intensa",
    "febre alta",
    "dor intensa",
    "mal-estar generalizado",
    "piora significativa",
    "não responde",
    "inconsciente",
    "não consegue falar",
    "fala arrastada",
    "voz trêmula",
    "sangramento",
    "queda",
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_marks.lower()


def find_critical_terms(
    text: str,
    *,
    terms: tuple[str, ...] | None = None,
) -> list[str]:
    """Retorna Termos Críticos presentes no texto (match sem acento, com fronteira)."""
    catalog = terms if terms is not None else CRITICAL_TERMS_PT
    norm = _normalize(text)
    found: list[str] = []
    for term in catalog:
        pattern = r"\b" + re.escape(_normalize(term)) + r"\b"
        if re.search(pattern, norm):
            found.append(term)
    return found
