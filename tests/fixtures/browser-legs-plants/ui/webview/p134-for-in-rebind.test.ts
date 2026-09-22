import { test } from "node:test";
const pw = require("playwright");
let name = "chromium";
for (name in { firefox: 1 }) {}
test("p134", async () => { const b = await pw[name].launch(); await b.close(); });
