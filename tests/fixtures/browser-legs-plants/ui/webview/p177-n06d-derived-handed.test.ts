import { test } from "node:test";
const pw = require("playwright");
const { firefox } = pw;
async function go(e: any): Promise<void> { const b = await e.launch(); await b.close(); }
test("p177", async () => { await go(firefox); });
