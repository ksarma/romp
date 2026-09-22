import { test } from "node:test";
const pw = require("playwright") ?? null;
test("p100", async () => { const b = await pw.webkit.launch(); await b.close(); });
