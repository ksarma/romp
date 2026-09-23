import { test } from "node:test";
import * as pw from "playwright";
async function go(b: any = pw): Promise<void> { const w = await b.firefox.launch(); await w.close(); }
test("p267", async () => { await go(); });
