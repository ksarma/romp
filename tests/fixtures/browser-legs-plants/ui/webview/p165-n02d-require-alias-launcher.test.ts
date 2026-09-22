import { test } from "node:test";
const r = require;
const leg = r("./real-viewer-leg");
test("p165", async (t) => { await leg.inBrowser(t, async () => {}); });
