import { test } from "node:test";
const pw = require("playwright");
async function go(p: any = pw): Promise<void> { const b = await p.webkit.launch(); await b.close(); }
test("p263", async () => { await go(); });
