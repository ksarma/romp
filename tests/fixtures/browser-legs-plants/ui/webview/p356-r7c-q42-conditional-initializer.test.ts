import { test } from "node:test";
import { load } from "some-foreign-loader";
const name = process.env.CORE ? "playwright-core" : "playwright";
test("p356", async () => { const b = await load(name).firefox.launch(); await b.close(); });
