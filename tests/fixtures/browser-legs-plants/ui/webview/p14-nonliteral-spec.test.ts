import { test } from "node:test";
const spec = process.env.PW_PKG || "playwright";
const pw = require(spec);
test("p14", async () => { const b = await pw.chromium.launch(); await b.close(); });
