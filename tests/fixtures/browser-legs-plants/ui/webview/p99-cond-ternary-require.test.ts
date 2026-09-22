import { test } from "node:test";
const pw = process.env.FLAG ? require("playwright") : null;
test("p99", async () => { const b = await pw.firefox.launch(); await b.close(); });
