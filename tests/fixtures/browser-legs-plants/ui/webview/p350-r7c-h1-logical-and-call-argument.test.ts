import { test } from "node:test";
import { load } from "some-foreign-loader";
test("p350", async () => { const b = await load(process.env.PLANT_ON && "playwright").firefox.launch(); await b.close(); });
