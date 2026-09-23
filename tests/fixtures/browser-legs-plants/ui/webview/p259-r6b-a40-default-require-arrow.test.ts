import { test } from "node:test";
const load = (r = require): any => { const s = "playwright"; return r(s); };
test("p259", async () => { const b = await load().firefox.launch(); await b.close(); });
