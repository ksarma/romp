import { test } from "node:test";
import { createRequire } from "node:module";
let req: any;
req = createRequire(__filename);
test("p168", async () => { const b = await req("playwright").webkit.launch(); await b.close(); });
