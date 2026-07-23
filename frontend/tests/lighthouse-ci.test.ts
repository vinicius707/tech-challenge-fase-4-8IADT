import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

describe("lighthouse CI gate (T7.13)", () => {
  const ci = readFileSync(
    path.join(repoRoot, ".github", "workflows", "ci.yml"),
    "utf8",
  );

  it("define job ou step Lighthouse no workflow CI", () => {
    expect(ci.toLowerCase()).toMatch(/lighthouse/);
    expect(ci).toMatch(/lighthouse:check|lighthouse-baseline\.mjs.*--check/);
  });

  it("sobe build de produção do frontend antes do check", () => {
    expect(ci).toMatch(/npm run build/);
    expect(ci).toMatch(/npm start|next start/);
  });

  it("publica artefatos HTML/JSON do check (não o baseline)", () => {
    expect(ci).toMatch(/upload-artifact/);
    expect(ci).toMatch(/docs\/perf\/check/);
    expect(ci).not.toMatch(/path:\s*docs\/perf\/baseline/);
  });

  it("não publica GHCR neste job (Épico 8)", () => {
    expect(ci.toLowerCase()).not.toMatch(/ghcr\.io|docker\/login-action/);
  });
});
