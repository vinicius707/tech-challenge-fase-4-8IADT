#!/usr/bin/env node
/**
 * Gera baseline Lighthouse (desktop) para /login e /pacientes.
 * Pré-requisito: frontend em LIMEN_BASE_URL (padrão http://127.0.0.1:3000).
 *
 * Uso:
 *   cd frontend && npm run lighthouse:baseline
 *   # ou na raiz:
 *   node scripts/lighthouse-baseline.mjs
 */
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const frontendRoot = path.join(repoRoot, "frontend");
const require = createRequire(path.join(frontendRoot, "package.json"));
const lighthouse = require("lighthouse").default;
const chromeLauncher = require("chrome-launcher");
const puppeteer = require("puppeteer-core");

const outDir = path.join(repoRoot, "docs", "perf", "baseline");
const baseUrl = (process.env.LIMEN_BASE_URL || "http://127.0.0.1:3000").replace(
  /\/$/,
  "",
);

const SESSION_PAYLOAD = JSON.stringify({
  state: {
    accessToken: "lh-baseline-token",
    refreshToken: "lh-baseline-refresh",
    username: "medico",
    role: "medico",
  },
  version: 0,
});

const LH_FLAGS = {
  output: ["json", "html"],
  logLevel: "error",
  onlyCategories: ["performance", "accessibility", "best-practices", "seo"],
  formFactor: "desktop",
  screenEmulation: {
    mobile: false,
    width: 1350,
    height: 940,
    deviceScaleFactor: 1,
    disabled: false,
  },
  throttlingMethod: "simulate",
  disableStorageReset: true,
};

function gitSha() {
  try {
    return execSync("git rev-parse --short HEAD", {
      cwd: repoRoot,
      encoding: "utf8",
    }).trim();
  } catch {
    return "unknown";
  }
}

async function writeReport(slug, result) {
  const reports = Array.isArray(result.report) ? result.report : [result.report];
  const jsonReport =
    reports.find((r) => typeof r === "string" && r.trimStart().startsWith("{")) ??
    reports[0];
  const htmlReport =
    reports.find((r) => typeof r === "string" && r.includes("<html")) ??
    reports[1] ??
    reports[0];

  await writeFile(path.join(outDir, `${slug}.report.json`), jsonReport);
  await writeFile(path.join(outDir, `${slug}.report.html`), htmlReport);

  const cats = result.lhr.categories;
  return {
    slug,
    url: result.lhr.finalDisplayedUrl || result.lhr.finalRequestedUrl || result.lhr.requestedUrl,
    scores: {
      performance: Math.round((cats.performance?.score ?? 0) * 100),
      accessibility: Math.round((cats.accessibility?.score ?? 0) * 100),
      bestPractices: Math.round((cats["best-practices"]?.score ?? 0) * 100),
      seo: Math.round((cats.seo?.score ?? 0) * 100),
    },
  };
}

async function main() {
  await mkdir(outDir, { recursive: true });
  const sha = gitSha();
  const generatedAt = new Date().toISOString();

  const chrome = await chromeLauncher.launch({
    chromeFlags: ["--headless=new", "--no-sandbox", "--disable-gpu"],
  });

  const browser = await puppeteer.connect({
    browserURL: `http://127.0.0.1:${chrome.port}`,
    defaultViewport: null,
  });

  try {
    const loginPage = await browser.newPage();
    const loginResult = await lighthouse(
      `${baseUrl}/login`,
      { ...LH_FLAGS, port: chrome.port },
      undefined,
      loginPage,
    );
    await loginPage.close();
    const login = await writeReport("login-desktop", loginResult);

    const pacientesPage = await browser.newPage();
    await pacientesPage.goto(`${baseUrl}/login`, {
      waitUntil: "networkidle0",
    });
    await pacientesPage.evaluate((payload) => {
      localStorage.setItem("limen-session", payload);
    }, SESSION_PAYLOAD);
    const pacientesResult = await lighthouse(
      `${baseUrl}/pacientes`,
      { ...LH_FLAGS, port: chrome.port },
      undefined,
      pacientesPage,
    );
    await pacientesPage.close();
    const pacientes = await writeReport("pacientes-desktop", pacientesResult);

    const summary = {
      generatedAt,
      gitSha: sha,
      baseUrl,
      formFactor: "desktop",
      routes: [login, pacientes],
      note: "Baseline do Épico 4 — sem gate de CI. Sessão de /pacientes é token sintético só para renderizar o shell autenticado.",
    };
    await writeFile(
      path.join(outDir, "summary.json"),
      `${JSON.stringify(summary, null, 2)}\n`,
    );

    console.log(JSON.stringify(summary, null, 2));
  } finally {
    await browser.disconnect();
    await chrome.kill();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
