import { test } from "node:test";
const r = module.require;
test("p187", async () => { const b = await r("playwright").firefox.launch(); await b.close(); });
