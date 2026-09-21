import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
const pw = require("playwright");
const { launch } = pw.chromium;
test("p5", async (t) => { await inBrowser(t, async () => {}); const b = await launch(); await b.close(); });
