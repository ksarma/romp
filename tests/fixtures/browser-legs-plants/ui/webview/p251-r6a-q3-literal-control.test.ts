import { test } from "node:test";
const spec = "./decoy-helper";
function load(spec: string): any { return require(spec); }
const pw = load("playwright");
test("p251", async () => { const b = await pw.firefox.launch(); await b.close(); });
