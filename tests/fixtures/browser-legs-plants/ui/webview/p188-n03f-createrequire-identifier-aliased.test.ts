import { test } from "node:test";
import { createRequire } from "node:module";
const make = createRequire;
const req = make(__filename);
test("p188", async () => { const b = await req("playwright").webkit.launch(); await b.close(); });
