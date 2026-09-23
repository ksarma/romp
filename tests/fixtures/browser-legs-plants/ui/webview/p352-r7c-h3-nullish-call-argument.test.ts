import { test } from "node:test";
import { load } from "some-foreign-loader";
test("p352", async () => { const b = await load(process.env.PLANT_PKG ?? "playwright").firefox.launch(); await b.close(); });
