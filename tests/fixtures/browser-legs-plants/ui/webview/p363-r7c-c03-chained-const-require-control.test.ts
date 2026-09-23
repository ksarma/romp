import { test } from "node:test";
const PKG = "playwright";
const SPEC = PKG;
const pw = require(SPEC);
test("p363", async () => { const b = await pw.firefox.launch(); await b.close(); });
