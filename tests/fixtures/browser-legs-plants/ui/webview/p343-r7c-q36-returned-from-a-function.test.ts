import { test } from "node:test";
import { load } from "some-foreign-loader";
function pkg(): string { return "playwright"; }
test("p343", async () => { const b = await load(pkg()).firefox.launch(); await b.close(); });
