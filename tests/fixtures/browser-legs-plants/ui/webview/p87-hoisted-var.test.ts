import { test } from "node:test";
{ var pw = require("playwright"); }
test("p87", async () => { const b = await pw.firefox.launch(); await b.close(); });
