import { test } from "node:test";
import { createRequire as cr } from "node:module";
const req = cr(__filename);
test("p170", async () => { const b = await req("playwright").firefox.launch(); await b.close(); });
