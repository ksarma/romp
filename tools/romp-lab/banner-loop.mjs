// The scripted RELOAD-BANNER loop (T119, the user 2026-08-27: a restart onto real UI changes never
// raised the banner — the restart path rebuilt nothing, so no drift existed for any raiser). This
// phase asserts the banner CONTRACT end to end on the real stack, with zero model spend:
//   1. a fresh page shows no banner
//   2. a dist rebuild (simulated: an mtime bump on the LAB's OWN dist copy — ROMP_DIST_DIR) raises
//      the shell's #rstale within one heartbeat via the shim's ka dv-compare (the window is kept
//      tighter than the shell's 30s /version poll, so it proves the EVENT path, not the poll)
//   3. the banner LATCHES across live pushes (wsFresh must never retire a build prompt)
//   4. Reload answers it: the reloaded page (fresh LOADEDV) shows no banner — click-to-reload only,
//      never auto (the standing rule)
//   5. the RECONNECT shape: the kernel is killed and relaunched (a real restart severing every ws);
//      after the page reconnects, a fresh dist bump must banner again — the reconnected socket's
//      drift detection, the T119 candidate (b)
// Exits non-zero naming the first diverging phase; screenshots per phase in $LAB/shots.
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const require2 = createRequire(path.join(ROOT, "vscode-extension", "package.json"));
const { chromium } = require2("playwright");

const PORT = process.env.PORT, TOKEN = process.env.TOKEN, LAB = process.env.LAB_DIR;
const KPID = Number(process.env.KPID || 0);
const KERNEL_BIN = process.env.KERNEL_BIN || path.join(ROOT, "bin", "romp-kernel");
const DIST = process.env.ROMP_DIST_DIR;   // the lab's own copy — bumps here never touch live viewers
const KA = Number(process.env.ROMP_WS_KEEPALIVE || 10);
const shots = path.join(LAB, "shots");
let phaseN = 0;
const fails = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const b = await chromium.launch();
const page = await b.newPage({ viewport: { width: 1280, height: 850 } });
page.on("pageerror", (e) => console.log("PAGEERR", String(e)));
const shot = async (name) => page.screenshot({ path: path.join(shots, `bn${String(++phaseN).padStart(2, "0")}-${name}.png`) });
const check = (name, ok, detail = "") => {
  console.log(`${ok ? "PASS" : "FAIL"} banner:${name}${detail ? " — " + detail : ""}`);
  if (!ok) fails.push(name);
};
const bannerShown = () => page.evaluate(() => {
  const box = document.getElementById("rstale");
  return !!box && box.classList.contains("show") ? box.querySelector(".rs-msg").textContent : "";
});
const bumpDist = () => {
  const now = new Date();
  for (const f of fs.readdirSync(DIST)) if (f.endsWith(".js")) fs.utimesSync(path.join(DIST, f), now, now);
};
const waitBanner = async (ms) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const m = await bannerShown();
    if (m) return m;
    await sleep(200);
  }
  return "";
};
const healthy = async () => {
  try { const r = await fetch(`http://127.0.0.1:${PORT}/healthz`); return r.ok; } catch { return false; }
};

// ── 1. fresh page: no banner ──
await page.goto(`http://127.0.0.1:${PORT}/?token=${TOKEN}`);
await page.waitForSelector("#rstale", { state: "attached", timeout: 20000 });
await sleep(2 * KA * 1000 + 1000);            // two heartbeats of quiet — nothing may raise on a fresh page
check("fresh-page-quiet", !(await bannerShown()), await bannerShown());
await shot("fresh");

// ── 2. dist bump → banner within one heartbeat (the shim's ka path, tighter than the 30s poll) ──
bumpDist();
const raised = await waitBanner(2 * KA * 1000 + 3000);
check("raise-on-drift", raised.includes("newer romp build"), raised || "(never shown)");
await shot("raised");

// ── 3. the build prompt LATCHES across live pushes (wsFresh keeps it) ──
await sleep(3000);
check("latch-across-pushes", (await bannerShown()).includes("newer romp build"));

// ── 4. click-to-reload answers it — and only a click ever does ──
await page.click("#rstale-reload");
await page.waitForSelector("#rstale", { state: "attached", timeout: 20000 });
await sleep(2 * KA * 1000 + 1000);
check("reload-answers", !(await bannerShown()), await bannerShown());
await shot("reloaded");

// ── 5. the reconnect shape: kernel killed + relaunched, then a fresh drift must still banner ──
process.kill(KPID, "SIGTERM");
const log2 = fs.openSync(path.join(LAB, "kernel.log"), "a");
const k2 = spawn(KERNEL_BIN, [], { env: process.env, stdio: ["ignore", log2, log2], detached: true });
k2.unref();
fs.writeFileSync(path.join(LAB, "kernel.pid"), String(k2.pid));
const t0 = Date.now();
while (!(await healthy()) && Date.now() - t0 < 30000) await sleep(500);
check("kernel-relaunched", await healthy());
// let the page's shims notice the drop and reconnect (onclose → retry), and the resync land
await sleep(8000);
bumpDist();
const raised2 = await waitBanner(2 * KA * 1000 + 3000);
check("raise-after-reconnect", raised2.includes("newer romp build"), raised2 || "(never shown)");
await shot("raised-after-reconnect");

await b.close();
if (fails.length) { console.log("banner loop FAILED:", fails.join(", ")); process.exit(1); }
console.log("banner loop: all phases green");
