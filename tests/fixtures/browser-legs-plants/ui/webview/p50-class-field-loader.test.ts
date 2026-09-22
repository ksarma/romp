import { test } from "node:test";
class Holder { pw = require("playwright"); }
test("p50", async () => { const b = await new Holder().pw.chromium.launch(); await b.close(); });
