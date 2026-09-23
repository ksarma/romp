import { test } from "node:test";
let chromium: any = null;
try { chromium = require("playwright").chromium; } catch { chromium = null; }
test("p277", async () => { if (!chromium) return; const b = await chromium.launch(); await b.close(); });
