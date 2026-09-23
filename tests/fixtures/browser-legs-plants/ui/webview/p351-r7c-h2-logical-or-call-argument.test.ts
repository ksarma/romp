import { test } from "node:test";
import { load } from "some-foreign-loader";
test("p351", async () => { const b = await load(process.env.PLANT_PKG || "playwright").firefox.launch(); await b.close(); });
