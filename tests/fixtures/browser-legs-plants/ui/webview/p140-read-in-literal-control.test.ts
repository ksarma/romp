import { test } from "node:test";
const pw = require("playwright");
let name = "chromium";
const seen = { name }; void seen;
test("p140", async () => { const b = await pw[name].launch(); await b.close(); });
