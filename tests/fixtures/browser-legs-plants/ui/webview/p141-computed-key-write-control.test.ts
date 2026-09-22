import { test } from "node:test";
const pw = require("playwright");
let name = "chromium";
const o: Record<string, number> = {}; o[name] = 1;
test("p141", async () => { const b = await pw[name].launch(); await b.close(); });
