import { test } from "node:test";
import { load } from "some-foreign-loader";
const name = "playwright";
test("p332", async () => { const b = await load(name).firefox.launch(); await b.close(); });
