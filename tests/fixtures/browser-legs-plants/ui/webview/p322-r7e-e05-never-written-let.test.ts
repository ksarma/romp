import { test } from "node:test";
let spec: any;
const pw = require(spec);
test("p322", async () => { const b = await pw.firefox.launch(); await b.close(); });
