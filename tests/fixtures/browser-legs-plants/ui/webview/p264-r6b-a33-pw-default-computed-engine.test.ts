import { test } from "node:test";
const pw = require("playwright");
async function go(p: any = pw): Promise<void> { const e = "webkit"; const b = await p[e].launch(); await b.close(); }
test("p264", async () => { const b = await pw.firefox.launch(); await b.close(); await go(); });
