import { test } from "node:test";
import { createRequire } from "node:module";
const pw = createRequire(__filename)("playwright");
test("p53", async () => { const b = await pw.chromium.launch(); await b.close(); });
