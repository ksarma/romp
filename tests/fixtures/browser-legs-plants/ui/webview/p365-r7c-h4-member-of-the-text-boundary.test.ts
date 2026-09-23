import { test } from "node:test";
import { load } from "some-foreign-loader";
test("p365", async () => { const b = await load("playwright".trim()).firefox.launch(); await b.close(); });
