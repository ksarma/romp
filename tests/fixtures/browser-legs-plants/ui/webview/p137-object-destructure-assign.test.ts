import { test } from "node:test";
const pw = require("playwright");
let name = "chromium";
({ name } = { name: "webkit" });
test("p137", async () => { const b = await pw[name].launch(); await b.close(); });
