import { test } from "node:test";
let spec = "playwright";
const pw = require(spec);
test("p245", async () => { const b = await pw.firefox.launch(); await b.close(); });
