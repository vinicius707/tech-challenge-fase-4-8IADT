import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  ABSOLUTE_LIMITS,
  REGRESSION_TOLERANCE,
  evaluateGate,
  formatGateFailures,
  median,
  medianRouteScores,
  scoreFloor,
} from "../../scripts/lighthouse-gate.mjs";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

describe("lighthouse gate (T7.12)", () => {
  it("define pisos absolutos e tolerância de regressão", () => {
    expect(ABSOLUTE_LIMITS.performance).toBe(90);
    expect(ABSOLUTE_LIMITS.accessibility).toBe(95);
    expect(ABSOLUTE_LIMITS.bestPractices).toBe(90);
    expect(REGRESSION_TOLERANCE).toBe(2);
  });

  it("piso = max(absoluto, baseline − tolerância); baseline &lt; absoluto → só regressão", () => {
    expect(scoreFloor("performance", 97)).toBe(95); // 97−2=95 > 90
    expect(scoreFloor("performance", 88)).toBe(86); // baseline&lt;90 → 88−2
    expect(scoreFloor("accessibility", 100)).toBe(98); // 100−2
    expect(scoreFloor("bestPractices", 96)).toBe(94); // 96−2
  });

  it("passa quando scores ≥ piso restritivo", () => {
    const baseline = JSON.parse(
      readFileSync(
        path.join(repoRoot, "docs/perf/baseline/summary.json"),
        "utf8",
      ),
    );
    const current = {
      routes: baseline.routes.map((r: { slug: string; scores: object }) => ({
        slug: r.slug,
        scores: { ...r.scores },
      })),
    };
    // Login baseline histórico 88 (&lt; absoluto 90): piso = 86 (só regressão).
    // Mantém scores iguais ao baseline → deve passar.
    const result = evaluateGate(current, baseline);
    expect(result.ok).toBe(true);
    expect(result.failures).toEqual([]);
  });

  it("falha no piso absoluto quando baseline já está ≥ absoluto", () => {
    const baseline = {
      routes: [
        {
          slug: "login-desktop",
          scores: {
            performance: 92,
            accessibility: 100,
            bestPractices: 100,
            seo: 100,
          },
        },
      ],
    };
    const current = {
      routes: [
        {
          slug: "login-desktop",
          scores: {
            performance: 89, // &lt; max(90, 90)=90
            accessibility: 100,
            bestPractices: 100,
            seo: 100,
          },
        },
      ],
    };
    const result = evaluateGate(current, baseline);
    expect(result.ok).toBe(false);
    expect(result.failures).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          route: "login-desktop",
          category: "performance",
          score: 89,
          baseline: 92,
          floor: 90,
          delta: -3,
        }),
      ]),
    );
  });

  it("com baseline &lt; absoluto, falha só por regressão além da tolerância", () => {
    const baseline = {
      routes: [
        {
          slug: "login-desktop",
          scores: {
            performance: 88,
            accessibility: 100,
            bestPractices: 100,
            seo: 100,
          },
        },
      ],
    };
    const current = {
      routes: [
        {
          slug: "login-desktop",
          scores: {
            performance: 85, // 88−2=86 → falha; absoluto 90 não se aplica ainda
            accessibility: 100,
            bestPractices: 100,
            seo: 100,
          },
        },
      ],
    };
    const result = evaluateGate(current, baseline);
    expect(result.ok).toBe(false);
    expect(result.failures[0]).toMatchObject({
      route: "login-desktop",
      category: "performance",
      score: 85,
      baseline: 88,
      floor: 86,
      delta: -3,
    });
  });

  it("falha por regressão mesmo acima do piso absoluto", () => {
    const baseline = {
      routes: [
        {
          slug: "pacientes-desktop",
          scores: {
            performance: 97,
            accessibility: 100,
            bestPractices: 96,
            seo: 100,
          },
        },
      ],
    };
    const current = {
      routes: [
        {
          slug: "pacientes-desktop",
          scores: {
            performance: 94, // ≥90 abs, mas 97−2=95 → falha
            accessibility: 100,
            bestPractices: 96,
            seo: 100,
          },
        },
      ],
    };
    const result = evaluateGate(current, baseline);
    expect(result.ok).toBe(false);
    expect(result.failures[0]).toMatchObject({
      route: "pacientes-desktop",
      category: "performance",
      score: 94,
      baseline: 97,
      floor: 95,
      delta: -3,
    });
  });

  it("SEO não entra no gate (só categorias gated)", () => {
    const baseline = {
      routes: [
        {
          slug: "login-desktop",
          scores: {
            performance: 90,
            accessibility: 100,
            bestPractices: 100,
            seo: 100,
          },
        },
      ],
    };
    const current = {
      routes: [
        {
          slug: "login-desktop",
          scores: {
            performance: 90,
            accessibility: 100,
            bestPractices: 100,
            seo: 50,
          },
        },
      ],
    };
    expect(evaluateGate(current, baseline).ok).toBe(true);
  });

  it("mensagem aponta rota, categoria e delta", () => {
    const failures = [
      {
        route: "login-desktop",
        category: "performance",
        score: 87,
        baseline: 88,
        floor: 90,
        delta: -1,
      },
    ];
    const text = formatGateFailures(failures);
    expect(text).toMatch(/login-desktop/);
    expect(text).toMatch(/performance/);
    expect(text).toMatch(/delta/i);
    expect(text).toMatch(/-1/);
  });

  it("mediana estabiliza scores entre runs", () => {
    expect(median([88, 95, 90])).toBe(90);
    expect(median([85, 88])).toBe(87);
    const routes = medianRouteScores([
      [
        {
          slug: "login-desktop",
          url: "/login",
          scores: {
            performance: 88,
            accessibility: 100,
            bestPractices: 100,
            seo: 100,
          },
        },
      ],
      [
        {
          slug: "login-desktop",
          url: "/login",
          scores: {
            performance: 95,
            accessibility: 100,
            bestPractices: 100,
            seo: 100,
          },
        },
      ],
      [
        {
          slug: "login-desktop",
          url: "/login",
          scores: {
            performance: 90,
            accessibility: 100,
            bestPractices: 100,
            seo: 100,
          },
        },
      ],
    ]);
    expect(routes[0].scores.performance).toBe(90);
  });

  it("reutiliza a mesma regra no CI (job Lighthouse)", () => {
    const ci = readFileSync(
      path.join(repoRoot, ".github", "workflows", "ci.yml"),
      "utf8",
    );
    expect(ci).toMatch(/lighthouse:check/);
    expect(ci).toMatch(/LIMEN_LH_RUNS:\s*["']3["']/);
  });
});
