import { test } from "node:test";
let leg: any = null;
try { leg = require("./real-viewer-leg"); } catch { leg = null; }
test("p197", async (t) => { await leg.inBrowser(t, async () => {}); });
