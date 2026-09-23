import { test } from "node:test";
var spec = "./decoy-helper";
spec = "playwright";
const pw = require(spec);
test("p238", async () => { const b = await pw.webkit.launch(); await b.close(); });
