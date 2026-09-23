import { test } from "node:test";
class C { static { var spec = "./decoy-helper"; void spec; } }
void C;
const spec = "playwright";
const pw = require(spec);
test("p317", async () => { const b = await pw.firefox.launch(); await b.close(); });
