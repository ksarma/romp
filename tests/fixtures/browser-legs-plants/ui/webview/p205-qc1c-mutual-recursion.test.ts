import { test } from "node:test";
const pw = require("playwright");
async function a(e: string): Promise<void> { return b(e); }
async function b(e: string): Promise<void> { if (e === "") return a(e); const br = await pw[e].launch(); await br.close(); }
test("p205", async () => { await a("chromium"); });
