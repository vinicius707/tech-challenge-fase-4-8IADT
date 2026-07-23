"use client";

import dynamic from "next/dynamic";

const chartLoading = () => (
  <p className="text-sm text-muted-foreground" aria-live="polite">
    Carregando gráfico…
  </p>
);

/** Lazy Recharts — só rotas estrela (ADR 0027). */
export const LazyRiskTrendChart = dynamic(
  () =>
    import("@/components/charts/risk-trend-chart").then(
      (mod) => mod.RiskTrendChart,
    ),
  { ssr: false, loading: chartLoading },
);

export const LazyModalityScoresChart = dynamic(
  () =>
    import("@/components/charts/modality-scores-chart").then(
      (mod) => mod.ModalityScoresChart,
    ),
  { ssr: false, loading: chartLoading },
);
