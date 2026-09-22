import { test } from "node:test";
const pw = require("playwright");
var name = "chromium";
for (var name in { firefox: 1 }) {}
test("p152", async () => { const b = await pw[name].launch(); await b.close(); });
