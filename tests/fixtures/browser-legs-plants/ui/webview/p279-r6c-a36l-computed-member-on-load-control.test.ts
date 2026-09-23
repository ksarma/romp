import { test } from "node:test";
async function use(p: any): Promise<void> { const w = await p.launch(); await w.close(); }
test("p279", async () => { const k = process.env.E as string; await use(require("playwright")[k]); });
