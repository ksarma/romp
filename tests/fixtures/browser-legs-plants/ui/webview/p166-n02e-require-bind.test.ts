import { test } from "node:test";
const r = require.bind(null);
test("p166", async () => { const b = await r("playwright").webkit.launch(); await b.close(); });
