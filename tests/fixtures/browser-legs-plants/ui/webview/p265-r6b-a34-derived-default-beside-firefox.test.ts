import { test } from "node:test";
const pw = require("playwright");
const { webkit } = pw;
async function go(e: any = webkit): Promise<void> { const b = await e.launch(); await b.close(); }
test("p265", async () => { const b = await pw.firefox.launch(); await b.close(); await go(); });
