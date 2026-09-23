import { test } from "node:test";
import { createRequire } from "node:module";
const req = createRequire(__filename);
let spec = "./decoy-helper";
spec = "playwright";
const pw = req(spec);
test("p241", async () => { const b = await pw.firefox.launch(); await b.close(); });
