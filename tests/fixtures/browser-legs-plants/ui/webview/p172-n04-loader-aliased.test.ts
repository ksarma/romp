import { test } from "node:test";
import { createRequire } from "node:module";
const req = createRequire(__filename);
const load = req;
test("p172", async () => { const b = await load("playwright").firefox.launch(); await b.close(); });
