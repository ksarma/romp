import { test } from "node:test";
const pw = require("playwright");
async function inEngine(t: any, name: string) { void t; const b = await pw[name].launch(); await b.close(); }
test("p28", async (t) => { await inEngine(t, "chromium"); await inEngine(t, "webkit"); });
