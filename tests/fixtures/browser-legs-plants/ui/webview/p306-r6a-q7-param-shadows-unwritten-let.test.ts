import { test } from "node:test";
let spec = "./decoy-helper";
const PW = "playwright";
function load(spec: string): any { return require(spec); }
const pw = load(PW);
test("p306", async () => { const b = await pw.firefox.launch(); await b.close(); });
