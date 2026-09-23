import { test } from "node:test";
const spec = "./decoy-helper";
const PW = "playwright";
function load(s: string): any { return require(s); }
const pw = load(PW);
test("p252", async () => { const b = await pw.firefox.launch(); await b.close(); });
