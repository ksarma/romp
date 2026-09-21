import { test } from "node:test";
const pw = require("playwright");
test("p24", async () => { const b = await pw.chromium.connectOverCDP("http://localhost:9222"); await b.close(); });
