import { test } from "node:test";
const pw = require("playwright");
function get(): any { return pw; }
test("p176", async () => { const b = await get().firefox.launch(); await b.close(); });
