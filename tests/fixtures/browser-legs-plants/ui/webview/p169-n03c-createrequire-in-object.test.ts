import { test } from "node:test";
import { createRequire } from "node:module";
const l = { req: createRequire(__filename) };
test("p169", async () => { const b = await l.req("playwright").firefox.launch(); await b.close(); });
