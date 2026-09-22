import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
const pw = require("playwright");
const draw = ([w, pw]: [number, number]) => { const c: any = {}; c.width = pw; return c.width + w; };
test("p44", async (t) => { draw([1, 2]); await inBrowser(t, async () => {}); const b = await pw.firefox.launch(); await b.close(); });
