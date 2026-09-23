import { test } from "node:test";
const pw = require("playwright");
async function go(engine: string, again: boolean): Promise<void> { if (again) return go(engine, false); const b = await pw[engine].launch(); await b.close(); }
test("p203", async () => { await go("chromium", true); });
