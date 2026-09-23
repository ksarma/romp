import { test } from "node:test";
import { load } from "some-foreign-loader";
test("p344", async () => { const b = await load(process.env.CORE ? "playwright-core" : "playwright").firefox.launch(); await b.close(); });
