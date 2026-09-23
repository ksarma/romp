import { test } from "node:test";
const tail = "wright";
test("a04 the package's name from a template with a const tail", async () => { const pw = await import(`play${tail}`); const b = await pw.firefox.launch(); await b.close(); });
