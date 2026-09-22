import { test } from "node:test";
const pw = require("playwright");
const o: any[] = [];
o[0] = pw.chromium;
test("p40", async () => { const b = await o[0].launch(); await b.close(); });
