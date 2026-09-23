import { test } from "node:test";
const pw = require("playwright");
const bag = { pw };
test("p275", async () => { const b = await pw.firefox.launch(); await b.close(); const w = await bag.pw.webkit.launch(); await w.close(); });
