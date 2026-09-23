import { test } from "node:test";
let spec = "./decoy-helper";
spec = "playwright";
const pw = require(spec);
test("p237", async () => { const b = await pw.firefox.launch(); await b.close(); });
