import { test } from "node:test";
const PW = { playwright: 1 };
function load(): any { for (const spec in PW) { return require(spec); } }
const pw = load();
test("p319", async () => { const b = await pw.firefox.launch(); await b.close(); });
