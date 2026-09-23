import { test } from "node:test";
import { createRequire } from "node:module";
const req = createRequire(__filename);
function load(r = req): any { const s = "playwright"; return r(s); }
test("p257", async () => { const b = await load().firefox.launch(); await b.close(); });
