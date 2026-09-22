import { test } from "node:test";
const pw = require("playwright");
var name = "chromium";
for (var name of ["firefox"]) {}
test("p151", async () => { const b = await pw[name].launch(); await b.close(); });
