import { test } from "node:test";
import { load } from "some-foreign-loader";
const name = process.env.PW_PKG ?? "playwright";
test("p357", async () => { const b = await load(name).firefox.launch(); await b.close(); });
