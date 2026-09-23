import { test } from "node:test";
import { load } from "some-foreign-loader";
test("p331", async () => { const b = await load({ spec: "playwright" }).firefox.launch(); await b.close(); });
