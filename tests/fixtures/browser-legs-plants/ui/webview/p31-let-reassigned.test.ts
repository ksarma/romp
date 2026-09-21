import { test } from "node:test";
const pw = require("playwright");
let name = "chromium";
name = "firefox";
test("p31", async () => { const b = await pw[name].launch(); await b.close(); });
