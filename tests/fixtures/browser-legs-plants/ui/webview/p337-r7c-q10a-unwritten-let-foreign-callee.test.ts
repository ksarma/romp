import { test } from "node:test";
import { load } from "some-foreign-loader";
let name = "playwright";
test("p337", async () => { const b = await load(name).firefox.launch(); await b.close(); });
