import { test } from "node:test";
const spec = "./decoy-helper";
let pw: any;
class C { static { var spec = "playwright"; pw = require(spec); } }
void C;
test("p315", async () => { const b = await pw.firefox.launch(); await b.close(); });
