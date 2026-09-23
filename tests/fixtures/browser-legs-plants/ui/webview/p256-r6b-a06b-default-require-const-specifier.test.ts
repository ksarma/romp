import { test } from "node:test";
function load(r = require): any { const s = "playwright"; return r(s); }
test("p256", async () => { const b = await load().firefox.launch(); await b.close(); });
