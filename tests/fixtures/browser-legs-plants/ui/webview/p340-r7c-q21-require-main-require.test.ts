import { test } from "node:test";
const name = "playwright";
const pw = require.main!.require(name);
test("p340", async () => { const b = await pw.firefox.launch(); await b.close(); });
