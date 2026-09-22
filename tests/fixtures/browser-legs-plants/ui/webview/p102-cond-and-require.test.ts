import { test } from "node:test";
const ok = !!process.env.FLAG;
const pw = ok && require("playwright");
test("p102", async () => { const b = await pw.webkit.launch(); await b.close(); });
