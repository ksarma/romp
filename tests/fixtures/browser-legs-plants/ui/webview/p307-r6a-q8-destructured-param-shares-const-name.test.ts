import { test } from "node:test";
const spec = "./decoy-helper";
const PW = "playwright";
function load({ spec }: { spec: string }): any { return require(spec); }
const pw = load({ spec: PW });
test("p307", async () => { const b = await pw.firefox.launch(); await b.close(); });
