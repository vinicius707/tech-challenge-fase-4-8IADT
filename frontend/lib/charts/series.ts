export type RiskTrendCaseInput = {
  id: string;
  riskScore: number | null;
  riskLevel: string | null;
  createdAt: string;
};

export type RiskTrendPoint = {
  label: string;
  score: number;
  level: string;
};

export type ModalityScoreInput = {
  modality: string;
  status: string;
  partialScore: number | null;
  partialLevel: string | null;
};

export type ModalityScorePoint = {
  modality: string;
  score: number;
  level: string;
};

/** Pontos de tendência: só Casos com score (ordem cronológica). */
export function buildRiskTrendPoints(
  cases: RiskTrendCaseInput[],
): RiskTrendPoint[] {
  return [...cases]
    .filter(
      (item): item is RiskTrendCaseInput & { riskScore: number } =>
        typeof item.riskScore === "number",
    )
    .sort(
      (a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
    )
    .map((item) => ({
      label: item.id,
      score: item.riskScore,
      level: item.riskLevel ?? "—",
    }));
}

/** Barras de score parcial só de modalidades `done` com score. */
export function buildModalityScorePoints(
  modalities: ModalityScoreInput[],
): ModalityScorePoint[] {
  return modalities
    .filter(
      (
        item,
      ): item is ModalityScoreInput & { partialScore: number } =>
        item.status === "done" && typeof item.partialScore === "number",
    )
    .map((item) => ({
      modality: item.modality,
      score: item.partialScore,
      level: item.partialLevel ?? "—",
    }));
}
