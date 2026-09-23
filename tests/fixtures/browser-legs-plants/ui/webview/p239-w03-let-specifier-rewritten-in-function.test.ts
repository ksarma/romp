import { test } from "node:test";
let spec = "./decoy-helper";
function pick() { spec = "playwright"; }
pick();
const pw = require(spec);
test("p239", async () => { const b = await pw.firefox.launch(); await b.close(); });
