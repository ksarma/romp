import { test } from "node:test";
import pw, { type Page } from "playwright";
test("p125", async () => { const b = await pw.chromium.launch(); const p: Page | null = null; void p; await b.close(); });
