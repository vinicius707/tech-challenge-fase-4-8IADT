/** TDD T7.9 — Recharts lazy (ADR 0027). */

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  buildModalityScorePoints,
  buildRiskTrendPoints,
  type RiskTrendPoint,
} from "@/lib/charts/series";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function readSrc(relative: string): string {
  return readFileSync(path.join(root, relative), "utf8");
}

describe("chart series helpers (T7.9)", () => {
  it("monta pontos de tendência a partir de Casos com score", () => {
    const points = buildRiskTrendPoints([
      {
        id: "c1",
        riskScore: 0.2,
        riskLevel: "BAIXO",
        createdAt: "2026-07-20T10:00:00Z",
      },
      {
        id: "c2",
        riskScore: 0.7,
        riskLevel: "ALTO",
        createdAt: "2026-07-21T10:00:00Z",
      },
      {
        id: "c3",
        riskScore: null,
        riskLevel: null,
        createdAt: "2026-07-22T10:00:00Z",
      },
    ]);
    expect(points).toEqual<RiskTrendPoint[]>([
      { label: "c1", score: 0.2, level: "BAIXO" },
      { label: "c2", score: 0.7, level: "ALTO" },
    ]);
  });

  it("monta barras de score parcial por modalidade done", () => {
    const points = buildModalityScorePoints([
      {
        modality: "vitals",
        status: "done",
        partialScore: 0.55,
        partialLevel: "MEDIO",
      },
      {
        modality: "audio",
        status: "failed",
        partialScore: null,
        partialLevel: null,
      },
      {
        modality: "video",
        status: "done",
        partialScore: 0.8,
        partialLevel: "ALTO",
      },
    ]);
    expect(points).toEqual([
      { modality: "vitals", score: 0.55, level: "MEDIO" },
      { modality: "video", score: 0.8, level: "ALTO" },
    ]);
  });
});

describe("Recharts lazy contract (T7.9 / ADR 0027)", () => {
  it("centraliza lazy load com next/dynamic e ssr false", () => {
    const src = readSrc("components/charts/lazy.tsx");
    expect(src).toMatch(/from\s+["']next\/dynamic["']/);
    expect(src).toMatch(/ssr:\s*false/);
    expect(src).not.toMatch(/from\s+["']recharts["']/);
  });

  it("componentes de gráfico importam recharts só no módulo charts/", () => {
    const risk = readSrc("components/charts/risk-trend-chart.tsx");
    const modality = readSrc("components/charts/modality-scores-chart.tsx");
    expect(risk).toMatch(/from\s+["']recharts["']/);
    expect(modality).toMatch(/from\s+["']recharts["']/);
  });

  it("rotas sem gráfico não importam recharts nem charts/", () => {
    for (const file of [
      "app/login/page.tsx",
      "app/pacientes/page.tsx",
      "app/page.tsx",
      "app/alertas/page.tsx",
    ]) {
      const src = readSrc(file);
      expect(src, file).not.toMatch(/recharts/);
      expect(src, file).not.toMatch(/components\/charts/);
      expect(src, file).not.toMatch(/@\/components\/charts/);
    }
  });

  it("detalhe de Paciente e Caso usam wrappers lazy", () => {
    const patient = readSrc("components/patients/patient-detail.tsx");
    const caso = readSrc("components/cases/case-detail.tsx");
    expect(patient).toMatch(/@\/components\/charts\/lazy/);
    expect(caso).toMatch(/@\/components\/charts\/lazy/);
    expect(patient).not.toMatch(/from\s+["']recharts["']/);
    expect(caso).not.toMatch(/from\s+["']recharts["']/);
  });
});
