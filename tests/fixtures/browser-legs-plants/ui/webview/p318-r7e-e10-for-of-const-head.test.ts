import { test } from "node:test";
const PW = ["playwright"];
function load(): any { for (const spec of PW) { return require(spec); } }
const pw = load();
test("p318", async () => { const b = await pw.firefox.launch(); await b.close(); });
