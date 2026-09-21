import { test } from "node:test";
const pw = require("playwright");
test("p18", async () => { const b = await pw.chromium.launch.call(pw.chromium); await b.close(); });
