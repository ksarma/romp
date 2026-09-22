import { test } from "node:test";
const r = require;
test("p162", async () => { const b = await r("playwright").webkit.launch(); await b.close(); });
