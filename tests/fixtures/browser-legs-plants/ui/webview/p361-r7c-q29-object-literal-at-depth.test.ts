import { test } from "node:test";
import { load } from "some-foreign-loader";
test("p361", async () => { const b = await load({ opts: { spec: "playwright" } }).firefox.launch(); await b.close(); });
