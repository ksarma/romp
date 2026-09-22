import { test } from "node:test";
test("p56", async () => { const b = await (await import("playwright")).chromium.launch(); await b.close(); });
