/**
 * Gate Lighthouse (E7.3 / T7.12): pisos absolutos + regressão vs baseline.
 *
 * Piso por categoria = max(absoluto, baseline − tolerância).
 * SEO é informado nos relatórios; não entra no gate.
 */

export const ABSOLUTE_LIMITS = Object.freeze({
  performance: 90,
  accessibility: 95,
  bestPractices: 90,
});

/** Pontos de score permitidos abaixo do baseline (regressão). */
export const REGRESSION_TOLERANCE = 2;

export const GATED_CATEGORIES = Object.freeze([
  "performance",
  "accessibility",
  "bestPractices",
]);

/**
 * @param {"performance"|"accessibility"|"bestPractices"} category
 * @param {number} baselineScore
 * @returns {number}
 */
export function scoreFloor(category, baselineScore) {
  const absolute = ABSOLUTE_LIMITS[category];
  if (absolute == null) {
    throw new Error(`Categoria sem piso absoluto: ${category}`);
  }
  return Math.max(absolute, baselineScore - REGRESSION_TOLERANCE);
}

/**
 * @typedef {{ slug: string, scores: Record<string, number> }} RouteScores
 * @typedef {{ routes: RouteScores[] }} SummaryLike
 * @typedef {{
 *   route: string,
 *   category: string,
 *   score: number,
 *   baseline: number,
 *   floor: number,
 *   delta: number,
 * }} GateFailure
 */

/**
 * @param {SummaryLike} current
 * @param {SummaryLike} baseline
 * @returns {{ ok: boolean, failures: GateFailure[] }}
 */
export function evaluateGate(current, baseline) {
  const failures = [];
  const baselineBySlug = new Map(
    (baseline.routes ?? []).map((r) => [r.slug, r]),
  );

  for (const route of current.routes ?? []) {
    const baseRoute = baselineBySlug.get(route.slug);
    if (!baseRoute) {
      failures.push({
        route: route.slug,
        category: "(missing-baseline)",
        score: NaN,
        baseline: NaN,
        floor: NaN,
        delta: NaN,
      });
      continue;
    }

    for (const category of GATED_CATEGORIES) {
      const score = route.scores?.[category];
      const baselineScore = baseRoute.scores?.[category];
      if (typeof score !== "number" || typeof baselineScore !== "number") {
        failures.push({
          route: route.slug,
          category,
          score: typeof score === "number" ? score : NaN,
          baseline: typeof baselineScore === "number" ? baselineScore : NaN,
          floor: NaN,
          delta: NaN,
        });
        continue;
      }

      const floor = scoreFloor(category, baselineScore);
      if (score < floor) {
        failures.push({
          route: route.slug,
          category,
          score,
          baseline: baselineScore,
          floor,
          delta: score - baselineScore,
        });
      }
    }
  }

  return { ok: failures.length === 0, failures };
}

/**
 * @param {GateFailure[]} failures
 * @returns {string}
 */
export function formatGateFailures(failures) {
  if (!failures.length) return "Lighthouse gate: ok.";
  const lines = failures.map((f) => {
    if (f.category === "(missing-baseline)") {
      return `- ${f.route}: sem entrada correspondente no baseline.`;
    }
    return (
      `- ${f.route} / ${f.category}: score=${f.score}, ` +
      `baseline=${f.baseline}, floor=${f.floor}, delta=${f.delta}`
    );
  });
  return ["Lighthouse gate: FALHOU", ...lines].join("\n");
}
