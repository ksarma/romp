import { test } from "node:test";
import { load } from "some-foreign-loader";
function open(spec = "playwright"): any { return load(spec); }
test("p354", async () => { const b = await open().firefox.launch(); await b.close(); });
