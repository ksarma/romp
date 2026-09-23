import { test } from "node:test";
const spec = "./decoy-helper";
namespace N { const spec = "playwright"; export const pw = require(spec); }
test("p314", async () => { const b = await N.pw.firefox.launch(); await b.close(); });
