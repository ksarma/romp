import { test } from "node:test";
const h: any = {};
h.leg = require("./real-viewer-leg");
test("p38", async (t) => { await h.leg.inBrowser(t, async () => {}); });
