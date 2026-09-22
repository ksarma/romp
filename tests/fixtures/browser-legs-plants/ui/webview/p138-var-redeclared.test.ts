import { test } from "node:test";
const pw = require("playwright");
var name = "chromium";
var name = "firefox";
test("p138", async () => { const b = await pw[name].launch(); await b.close(); });
