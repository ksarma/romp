import { test } from "node:test";
import { createRequire } from "node:module";
import { inBrowser } from "./real-viewer-leg";
const requireCjs = createRequire(process.cwd() + "/package.json");
let pw: any = null; try { pw = requireCjs("playwright"); } catch { pw = null; }
test("p4", async (t) => { await inBrowser(t, async () => {}); const c = await pw.chromium.launchPersistentContext("/tmp/x"); await c.close(); });
