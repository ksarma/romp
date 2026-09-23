import { test } from "node:test";
import { load } from "some-foreign-loader";
function* names(): Generator<string> { yield "playwright"; }
test("p353", async () => { const b = await load(names().next().value).firefox.launch(); await b.close(); });
