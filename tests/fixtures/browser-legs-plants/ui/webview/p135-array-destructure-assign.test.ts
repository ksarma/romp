import { test } from "node:test";
const pw = require("playwright");
let name = "chromium";
[name] = ["webkit"];
test("p135", async () => { const b = await pw[name].launch(); await b.close(); });
