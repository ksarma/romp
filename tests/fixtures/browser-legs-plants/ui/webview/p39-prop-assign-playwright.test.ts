import { test } from "node:test";
const pw = require("playwright");
const o: any = {};
o.pw = pw;
test("p39", async () => { const b = await o.pw.chromium.launch(); await b.close(); });
