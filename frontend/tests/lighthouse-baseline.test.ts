import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const baselineDir = path.join(repoRoot, "docs", "perf", "baseline");

describe("lighthouse baseline (T4.7)", () => {
  it("README descreve data, SHA, ambiente e regeneração", () => {
    const readmePath = path.join(baselineDir, "README.md");
    expect(existsSync(readmePath)).toBe(true);
    const readme = readFileSync(readmePath, "utf8");
    expect(readme).toMatch(/regener/i);
    expect(readme).toMatch(/desktop/i);
    expect(readme).toMatch(/commit|SHA|sha/i);
    expect(readme).toMatch(/login/i);
    expect(readme).toMatch(/pacientes/i);
    expect(readme).toMatch(/tolerância|tolerancia|regression|regressão/i);
    expect(readme).toMatch(/lighthouse:check|--check/);
  });

  it("persiste relatórios JSON das rotas mínimas", () => {
    expect(existsSync(path.join(baselineDir, "login-desktop.report.json"))).toBe(
      true,
    );
    expect(
      existsSync(path.join(baselineDir, "pacientes-desktop.report.json")),
    ).toBe(true);
  });

  it("CI não adiciona gate de Lighthouse (ainda T7.13)", () => {
    const ci = readFileSync(
      path.join(repoRoot, ".github", "workflows", "ci.yml"),
      "utf8",
    );
    expect(ci.toLowerCase()).not.toMatch(/lighthouse/);
  });
});
