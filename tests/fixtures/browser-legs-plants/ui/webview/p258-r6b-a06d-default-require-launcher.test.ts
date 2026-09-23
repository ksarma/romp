import { test } from "node:test";
function load(r = require): any { const s = "./real-viewer-leg"; return r(s); }
test("p258", async (t) => { await load().inBrowser(t, async () => {}, "firefox"); });
