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

  it("usa Node ≥22.19 no job Lighthouse (engine do lighthouse)", () => {
    expect(ci).toMatch(/node-version:\s*["']22\.19/);
  });

  it("não publica GHCR no job Lighthouse (publish fica no job de imagens)", () => {
    const lighthouseJob = ci.split(/^  [a-z0-9_-]+:/m).find((block) =>
      /lighthouse/i.test(block),
    );
    expect(lighthouseJob).toBeDefined();
    expect(lighthouseJob!.toLowerCase()).not.toMatch(
      /ghcr\.io|docker\/login-action|docker\/build-push-action/,
    );
  });

  it("o workflow tem publish GHCR só em main (Épico 8 / T8.2)", () => {
    expect(ci.toLowerCase()).toMatch(/ghcr\.io/);
    expect(ci).toMatch(/docker\/login-action/);
    expect(ci).toMatch(/refs\/heads\/main/);
    expect(ci).toMatch(/limen-backend|limen-frontend/);
  });
});
