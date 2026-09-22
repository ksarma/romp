import { test } from "node:test";
const pw = require("playwright");
let name = "chromium";
for (name of ["firefox"]) {}
test("p133", async () => { const b = await pw[name].launch(); await b.close(); });
