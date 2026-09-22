import { test } from "node:test";
const pw = require("playwright");
var name = "chromium";
for (let name of ["firefox"]) { void name; }
test("p155", async () => { const b = await pw[name].launch(); await b.close(); });
