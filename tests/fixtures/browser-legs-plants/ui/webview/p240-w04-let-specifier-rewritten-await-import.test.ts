import { test } from "node:test";
let spec = "./decoy-helper";
spec = "playwright";
test("p240", async () => { const pw = await import(spec); const b = await pw.firefox.launch(); await b.close(); });
