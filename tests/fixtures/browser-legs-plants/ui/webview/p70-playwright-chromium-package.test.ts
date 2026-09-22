import { test } from "node:test";
import { chromium } from "playwright-chromium";
test("p70", async () => { const b = await chromium.launch(); await b.close(); });
