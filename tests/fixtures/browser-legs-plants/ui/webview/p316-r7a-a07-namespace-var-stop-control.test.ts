import { test } from "node:test";
namespace N { var spec = "./decoy-helper"; void spec; }
const spec = "playwright";
const pw = require(spec);
test("p316", async () => { const b = await pw.firefox.launch(); await b.close(); });
