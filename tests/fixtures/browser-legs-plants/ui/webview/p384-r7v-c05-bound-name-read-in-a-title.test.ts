import { test } from "node:test";
const PKG = "playwright";
const pw = require(PKG);
test("p384 " + PKG, async () => { const b = await pw.firefox.launch(); await b.close(); });
