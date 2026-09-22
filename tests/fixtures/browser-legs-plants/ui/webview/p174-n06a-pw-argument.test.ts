import { test } from "node:test";
const pw = require("playwright");
async function go(p: any): Promise<void> { const b = await p.firefox.launch(); await b.close(); }
test("p174", async () => { await go(pw); });
