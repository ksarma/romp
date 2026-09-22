import { test } from "node:test";
const pw = require("playwright") || null;
test("p101", async () => { const b = await pw.firefox.launch(); await b.close(); });
