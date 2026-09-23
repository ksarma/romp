import { test } from "node:test";
const spec = "./decoy-helper";
const PW = "playwright";
function load(spec: string): any { return require(spec); }
const pw = load(PW);
test("p249", async () => { const b = await pw.firefox.launch(); await b.close(); });
