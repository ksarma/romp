import { test } from "node:test";
import { requireCjs, inBrowser } from "./real-viewer-leg";
let pw: any = null; try { pw = requireCjs("playwright"); } catch { pw = null; }
test("p25", async (t) => { await inBrowser(t, async () => {}); const b = await pw.chromium.launch(); await b.close(); });
