import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  ABSOLUTE_LIMITS,
  REGRESSION_TOLERANCE,
  evaluateGate,
  formatGateFailures,
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

  it("piso = max(absoluto, baseline − tolerância)", () => {
    expect(scoreFloor("performance", 97)).toBe(95); // 97−2=95 > 90
    expect(scoreFloor("performance", 88)).toBe(90); // abs 90 > 86
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
    // Ajusta /login perf ao piso absoluto (baseline histórico é 88).
    const login = current.routes.find(
      (r: { slug: string }) => r.slug === "login-desktop",
    );
    login.scores.performance = 90;

    const result = evaluateGate(current, baseline);
    expect(result.ok).toBe(true);
    expect(result.failures).toEqual([]);
  });

  it("falha no piso absoluto mesmo acima da regressão", () => {
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
            performance: 87, // delta −1 ≤ tolerância, mas < 90 absoluto
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
          score: 87,
          baseline: 88,
          floor: 90,
          delta: -1,
        }),
      ]),
    );
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

  it("CI ainda não adiciona gate nesta tarefa (T7.13)", () => {
    const ci = readFileSync(
      path.join(repoRoot, ".github", "workflows", "ci.yml"),
      "utf8",
    );
    expect(ci.toLowerCase()).not.toMatch(/lighthouse/);
  });
});
