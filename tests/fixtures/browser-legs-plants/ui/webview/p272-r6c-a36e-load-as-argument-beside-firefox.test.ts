import { test } from "node:test";
async function use(p: any): Promise<void> { const w = await p.webkit.launch(); await w.close(); }
test("p272", async () => { const b = await require("playwright").firefox.launch(); await b.close(); await use(require("playwright")); });
