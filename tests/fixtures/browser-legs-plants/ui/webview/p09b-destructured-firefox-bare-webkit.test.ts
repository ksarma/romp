import { test } from "node:test";
const pw = require("playwright");
const { firefox } = pw;
const engine = pw.webkit;
test("p9b", async () => { const b = await firefox.launch(); await b.close(); const c = await engine.launch(); await c.close(); });
