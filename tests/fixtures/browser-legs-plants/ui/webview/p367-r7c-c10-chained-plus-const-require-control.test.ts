import { test } from "node:test";
const PKG = "playwright";
const SPEC = PKG + "-core";
const pw = require(SPEC);
test("p367", async () => { const b = await pw.firefox.launch(); await b.close(); });
