import { test } from "node:test";
const pw = require("playwright");
for (const name of ["chromium", "firefox"]) test("p15b " + name, async () => { const b = await pw[name].launch(); await b.close(); });
