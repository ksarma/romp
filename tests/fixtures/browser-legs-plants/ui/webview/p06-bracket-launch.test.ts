import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
const pw = require("playwright");
test("p6", async (t) => { await inBrowser(t, async () => {}); const b = await pw.chromium["launch"](); await b.close(); });
