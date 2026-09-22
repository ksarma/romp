import { test } from "node:test";
const pw = process.env.A ? (process.env.B ? require("playwright") : null) : null;
test("p108", async () => { const b = await pw.webkit.launch(); await b.close(); });
