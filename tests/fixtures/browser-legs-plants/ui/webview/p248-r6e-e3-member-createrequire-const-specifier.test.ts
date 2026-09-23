import { test } from "node:test";
import * as mod from "node:module";
const make = mod.createRequire;
const req = make(__filename);
const spec = "playwright";
test("e3 member createRequire with a const specifier", async () => { const b = await req(spec).firefox.launch(); await b.close(); });
