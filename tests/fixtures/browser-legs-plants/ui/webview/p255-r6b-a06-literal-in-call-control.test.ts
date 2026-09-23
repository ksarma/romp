import { test } from "node:test";
function load(r = require): any { return r("playwright"); }
test("p255", async () => { const b = await load().firefox.launch(); await b.close(); });
