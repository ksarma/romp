import { test } from "node:test";
const pw = require("playwright");
async function inEngine(t: any, name: string, retry = 1): Promise<void> { void t; if (retry > 0) return inEngine(t, name, retry - 1); const b = await pw[name].launch(); await b.close(); }
test("p206", async (t) => { await inEngine(t, "chromium"); await inEngine(t, "webkit"); });
