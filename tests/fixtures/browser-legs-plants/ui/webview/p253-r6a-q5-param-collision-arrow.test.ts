import { test } from "node:test";
const spec = "./decoy-helper";
const PW = "playwright";
const load = (spec: string): any => require(spec);
const pw = load(PW);
test("p253", async () => { const b = await pw.firefox.launch(); await b.close(); });
