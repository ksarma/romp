import { test } from "node:test";
import { createRequire } from "node:module";
function loadPw(r: any): any { return r("playwright"); }
test("p167", async () => { const b = await loadPw(createRequire(__filename)).firefox.launch(); await b.close(); });
