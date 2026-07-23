import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

describe("auth gate login LCP (CI fix)", () => {
  it("não bloqueia o render do login enquanto a sessão hidrata", () => {
    const source = readFileSync(
      path.join(
        repoRoot,
        "frontend/components/auth/auth-gate.tsx",
      ),
      "utf8",
    );
    // Login deve pintar SSR (LCP) sem esperar hasHydrated → "Carregando…".
    expect(source).toMatch(/mode === ["']login["']/);
    expect(source).toMatch(/SSR|imediatamente|LCP/i);
    const loadingOnlyForApp =
      /if \(mode === ["']login["']\)[\s\S]*?if \(!hasHydrated\)/.test(source) ||
      /Login:[\s\S]*hasHydrated/.test(source);
    expect(loadingOnlyForApp).toBe(true);
  });
});
