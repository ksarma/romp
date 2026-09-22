import { test } from "node:test";
import { createRequire } from "node:module";
const req = createRequire(__filename);
function loadPw(r: any): any { return r("playwright"); }
test("p173", async () => { const b = await loadPw(req).webkit.launch(); await b.close(); });
