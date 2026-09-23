import { test } from "node:test";
import { load } from "some-foreign-loader";
const [head] = "playwright";
test("p369", async () => { const b = await load(head).firefox.launch(); await b.close(); });
