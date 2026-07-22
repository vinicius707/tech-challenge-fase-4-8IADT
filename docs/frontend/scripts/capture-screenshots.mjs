#!/usr/bin/env node
/**
 * Captura prints das telas do shell para docs/frontend/images/.
 * Pré-requisito: stack no ar (./scripts/start-limen.sh).
 *
 * Uso: node docs/frontend/scripts/capture-screenshots.mjs
 */
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../../..");
const frontendRoot = path.join(repoRoot, "frontend");
const outDir = path.join(repoRoot, "docs", "frontend", "images");
const require = createRequire(path.join(frontendRoot, "package.json"));
const chromeLauncher = require("chrome-launcher");
const puppeteer = require("puppeteer-core");

const baseUrl = (process.env.LIMEN_BASE_URL || "http://127.0.0.1:3000").replace(
  /\/$/,
  "",
);

function loadSeed() {
  try {
    const env = readFileSync(path.join(repoRoot, ".env"), "utf8");
    const get = (key, fallback) => {
      const m = env.match(new RegExp(`^${key}=(.*)$`, "m"));
      return (m ? m[1].trim() : fallback) || fallback;
    };
    return {
      username: get("SEED_MEDICO_USERNAME", "medico"),
      password: get("SEED_MEDICO_PASSWORD", "medico_dev_only"),
    };
  } catch {
    return { username: "medico", password: "medico_dev_only" };
  }
}

async function shot(page, name) {
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log("saved", file);
}

async function main() {
  await mkdir(outDir, { recursive: true });
  const seed = loadSeed();
  const chrome = await chromeLauncher.launch({
    chromeFlags: ["--headless=new", "--no-sandbox", "--window-size=1280,800"],
  });
  const browser = await puppeteer.connect({
    browserURL: `http://127.0.0.1:${chrome.port}`,
    defaultViewport: { width: 1280, height: 800 },
  });

  try {
    const page = await browser.newPage();

    await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle0" });
    await shot(page, "01-login");

    await page.type("#username", seed.username, { delay: 20 });
    await page.type("#password", seed.password, { delay: 20 });
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle0" }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForSelector("text/Início", { timeout: 15000 }).catch(() => {});
    await shot(page, "02-inicio");

    await page.goto(`${baseUrl}/pacientes`, { waitUntil: "networkidle0" });
    await page.waitForSelector("h1", { timeout: 15000 });
    // cria paciente se lista vazia
    const createBtn = await page.$("button");
    const buttons = await page.$$("button");
    for (const b of buttons) {
      const text = await page.evaluate((el) => el.textContent || "", b);
      if (/novo paciente/i.test(text)) {
        await b.click();
        await page.waitForNetworkIdle({ idleTime: 500, timeout: 15000 }).catch(() => {});
        break;
      }
    }
    await shot(page, "03-pacientes");

    const openLink = await page.$('a[href*="/pacientes/"]');
    if (openLink) {
      await Promise.all([
        page.waitForNavigation({ waitUntil: "networkidle0" }),
        openLink.click(),
      ]);
      await shot(page, "04-paciente-detalhe");

      const novoCaso = await page.$('a[href$="/novo-caso"]');
      if (novoCaso) {
        await Promise.all([
          page.waitForNavigation({ waitUntil: "networkidle0" }),
          novoCaso.click(),
        ]);
        await shot(page, "05-novo-caso");

        const vitalsPath = path.join(
          repoRoot,
          "data",
          "fixtures",
          "vitals",
          "vitals_medium.csv",
        );
        const input = await page.$("#vitals-csv");
        if (input) {
          await input.uploadFile(vitalsPath);
          await Promise.all([
            page.waitForNavigation({ waitUntil: "networkidle0", timeout: 30000 }),
            page.click('button[type="submit"]'),
          ]);
          // aguarda polling/risco
          await page.waitForFunction(
            () => {
              const t = document.body?.innerText || "";
              return /done|BAIXO|MEDIO|ALTO|falhou|timeout/i.test(t);
            },
            { timeout: 120000 },
          ).catch(() => {});
          await new Promise((r) => setTimeout(r, 1500));
          await shot(page, "06-caso-detalhe");
        }
      }
    }
  } finally {
    await browser.disconnect();
    await chrome.kill();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
