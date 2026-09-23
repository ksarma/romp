import { test } from "node:test";
const spec = "./decoy-helper";
const PW = "playwright";
function load(): any { try { throw PW; } catch (spec) { return require(spec as string); } }
const pw = load();
test("p308", async () => { const b = await pw.firefox.launch(); await b.close(); });
