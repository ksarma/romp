import { test } from "node:test";
declare const SPEC: string;
const pw = require(SPEC);
test("p321", async () => { const b = await pw.firefox.launch(); await b.close(); });
