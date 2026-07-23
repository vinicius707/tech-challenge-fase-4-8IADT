import { describe, expect, it } from "vitest";

import {
  AA_TEXT_MIN,
  AA_UI_MIN,
  contrastRatio,
  criticalThemePairs,
  relativeLuminance,
} from "@/lib/theme/contrast";

describe("theme contrast AA (T7.6)", () => {
  it("calcula contraste WCAG entre cinzas neutros", () => {
    const white = relativeLuminance(255, 255, 255);
    const nearBlack = relativeLuminance(23, 23, 23);
    expect(contrastRatio(white, nearBlack)).toBeGreaterThan(AA_TEXT_MIN);
  });

  it("mantém pares críticos light/dark acima do piso AA de texto", () => {
    for (const pair of criticalThemePairs) {
      const ratio = contrastRatio(
        relativeLuminance(...pair.fg),
        relativeLuminance(...pair.bg),
      );
      expect(ratio, pair.name).toBeGreaterThanOrEqual(pair.minRatio);
    }
  });

  it("exige piso AA de UI (3:1) nos controles primários", () => {
    const uiPairs = criticalThemePairs.filter((p) => p.minRatio === AA_UI_MIN);
    expect(uiPairs.length).toBeGreaterThan(0);
    for (const pair of uiPairs) {
      const ratio = contrastRatio(
        relativeLuminance(...pair.fg),
        relativeLuminance(...pair.bg),
      );
      expect(ratio, pair.name).toBeGreaterThanOrEqual(AA_UI_MIN);
    }
  });
});
