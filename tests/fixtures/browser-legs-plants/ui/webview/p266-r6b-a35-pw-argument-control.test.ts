import { test } from "node:test";
const pw = require("playwright");
async function go(p: any): Promise<void> { const b = await p.webkit.launch(); await b.close(); }
test("p266", async () => { const b = await pw.firefox.launch(); await b.close(); await go(pw); });
