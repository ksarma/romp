import { test } from "node:test";
import pw from "playwright-core";
test("p19", async () => { const b = await pw.webkit.launch(); await b.close(); });
