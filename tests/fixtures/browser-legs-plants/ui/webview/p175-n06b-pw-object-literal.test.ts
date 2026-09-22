import { test } from "node:test";
const pw = require("playwright");
const bag = { pw };
test("p175", async () => { const b = await bag.pw.webkit.launch(); await b.close(); });
