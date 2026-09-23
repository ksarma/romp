import { test } from "node:test";
import { load } from "some-foreign-loader";
test("p334", async () => { const b = await load("playwright").firefox.launch(); await b.close(); });
